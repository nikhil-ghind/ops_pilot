"""OpsPilot agent — Anthropic Claude with MCP function-calling loop."""
from __future__ import annotations
import json
import os
from typing import Iterator

import anthropic

from src.tools.fintech_tools import TOOL_MAP
from src.tools.schemas import TOOL_SCHEMAS

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

SYSTEM_PROMPT = """You are OpsPilot, an AI assistant for fintech operations.
You have access to 8 live tools that interact with accounts and transactions.

Operational guidelines:
- Always run_fraud_check before recommending a freeze
- When asked to investigate suspicious activity, get_account → list_transactions → run_fraud_check → flag/freeze as warranted
- Be precise: quote account IDs, transaction IDs, and amounts from tool results
- Escalate HIGH fraud risk automatically (freeze + flag); ask for confirmation on MEDIUM
- Never invent account data — always call tools
"""


def _call_tool(name: str, inputs: dict) -> str:
    fn = TOOL_MAP.get(name)
    if fn is None:
        return json.dumps({"error": f"Unknown tool: {name}"})
    result = fn(**inputs)
    return json.dumps(result, default=str)


def run_agent(query: str, max_rounds: int = 10) -> Iterator[str]:
    """
    Stream the agent's response. Yields text chunks and tool-use notifications.
    Runs Anthropic's tool-use agentic loop until no more tool calls are made.
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    messages = [{"role": "user", "content": query}]

    for _ in range(max_rounds):
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=TOOL_SCHEMAS,
            messages=messages,
        )

        tool_uses = [b for b in response.content if b.type == "tool_use"]
        text_blocks = [b for b in response.content if b.type == "text"]

        for block in text_blocks:
            yield block.text

        if response.stop_reason != "tool_use" or not tool_uses:
            break

        # Append assistant message then tool results
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for tu in tool_uses:
            yield f"\n[tool: {tu.name}({json.dumps(tu.input)})]\n"
            result = _call_tool(tu.name, tu.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": result,
            })
        messages.append({"role": "user", "content": tool_results})


def run_agent_sync(query: str) -> str:
    return "".join(run_agent(query))
