# Ops Pilot

## Project Overview

A conversational agent powered by Anthropic Claude that enables operators to perform complex operational tasks — resource allocation, cancellation, and linking — using plain natural language. The agent uses the Model Context Protocol (MCP) to expose structured tool schemas, and Claude's native function-calling to select and invoke the correct multi-step operation sequences. Operators interact via a CLI or thin HTTP interface; the agent handles disambiguation, confirmation prompts, and error recovery.

Key goals:
- Zero-code operator workflow execution via natural language
- Reliable multi-step operation chaining with rollback on failure
- Auditable tool call logs for every operator action
- Extensible tool schema registry for adding new operation types

---

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Language | Python | 3.11+ |
| LLM | Anthropic Claude (claude-3-5-sonnet-20241022) | anthropic 0.28+ |
| Tool Protocol | MCP (Model Context Protocol) | mcp 1.x |
| API Framework | FastAPI (optional HTTP interface) | 0.111+ |
| Config | pydantic-settings | 2.x |
| Logging | structlog | 24.x |
| Testing | pytest, pytest-asyncio | 8.x |
| CLI | click | 8.x |
| Persistence | SQLite (audit log) | built-in |

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                 Operator Interface Layer                  │
│    [CLI (click)]  OR  [FastAPI HTTP /chat endpoint]      │
└─────────────────────┬────────────────────────────────────┘
                      │ user message
┌─────────────────────▼────────────────────────────────────┐
│               Conversation Manager                        │
│  - Maintains message history (sliding window)            │
│  - Injects system prompt with tool descriptions          │
│  - Calls Anthropic Claude API with tools list            │
└─────────────────────┬────────────────────────────────────┘
                      │ tool_use blocks
┌─────────────────────▼────────────────────────────────────┐
│                  MCP Tool Dispatcher                      │
│  - Validates tool inputs against JSON schemas            │
│  - Routes to correct handler function                    │
│  - Writes audit log entry to SQLite                      │
│  - Returns tool_result back to Claude                    │
└─────────────────────┬────────────────────────────────────┘
                      │ handler calls
┌─────────────────────▼────────────────────────────────────┐
│               Operation Handlers                          │
│  [AllocateHandler] [CancelHandler] [LinkHandler]         │
│  [StatusHandler]   [ListHandler]                         │
└──────────────────────────────────────────────────────────┘
```

Components:
- **Conversation Manager**: Maintains full chat history, builds the messages list, calls Claude with `tools` parameter.
- **MCP Tool Registry**: Central registry of tool schemas (JSON Schema format) keyed by tool name.
- **MCP Tool Dispatcher**: On receiving a `tool_use` block from Claude, looks up the handler, validates inputs, executes, logs.
- **Operation Handlers**: Pure Python functions that implement business logic for each operation type.
- **Audit Logger**: SQLite-backed logger that records every tool invocation, inputs, outputs, operator ID, and timestamp.

---

## Phase 1 — Project Scaffolding and Configuration

**Goal:** Set up project structure, dependencies, config, and basic CLI skeleton.

### Tasks

1. Create directory structure:
   ```
   aiOpsMcpOrchestrator/
   ├── agent/
   │   ├── __init__.py
   │   ├── conversation.py
   │   ├── dispatcher.py
   │   └── registry.py
   ├── handlers/
   │   ├── __init__.py
   │   ├── allocate.py
   │   ├── cancel.py
   │   ├── link.py
   │   ├── status.py
   │   └── list_ops.py
   ├── prompts/
   │   └── system_prompt.txt
   ├── audit/
   │   ├── __init__.py
   │   └── logger.py
   ├── api/
   │   ├── __init__.py
   │   └── main.py
   ├── cli/
   │   ├── __init__.py
   │   └── chat.py
   ├── config/
   │   └── settings.py
   ├── tests/
   │   ├── test_dispatcher.py
   │   ├── test_handlers.py
   │   └── test_conversation.py
   ├── requirements.txt
   └── .env.example
   ```

2. Create `requirements.txt`:
   ```
   anthropic==0.28.0
   mcp==1.0.0
   fastapi==0.111.0
   uvicorn[standard]==0.30.0
   pydantic==2.7.4
   pydantic-settings==2.3.4
   structlog==24.1.0
   click==8.1.7
   pytest==8.2.2
   pytest-asyncio==0.23.7
   httpx==0.27.0
   python-dotenv==1.0.1
   ```

3. Create `.env.example`:
   ```
   ANTHROPIC_API_KEY=
   CLAUDE_MODEL=claude-3-5-sonnet-20241022
   MAX_TOKENS=4096
   MAX_HISTORY_TURNS=20
   AUDIT_DB_PATH=./audit/audit.db
   LOG_LEVEL=INFO
   API_KEY=
   ```

4. Create `config/settings.py`:
   - Class `Settings(BaseSettings)` with all fields above
   - `get_settings()` cached with `@lru_cache`

5. Create `prompts/system_prompt.txt`:
   - Write a detailed system prompt instructing Claude to:
     - Act as an operations assistant with access to allocation, cancellation, and linking tools
     - Always confirm destructive actions before executing
     - Ask for missing required parameters rather than assuming
     - Return structured summaries after multi-step operations
     - Never fabricate resource IDs; always use IDs returned by list/status tools

---

## Phase 2 — MCP Tool Schema Registry

**Goal:** Define all tool schemas following the MCP JSON Schema spec and register them in a central registry.

### Tasks

1. Implement `agent/registry.py`:
   - Class `ToolRegistry` with:
     - `tools: dict[str, dict]` — maps tool name to its full MCP schema
     - `register(schema: dict)` — validates schema has `name`, `description`, `input_schema` keys; stores it
     - `get_tools_list() -> list[dict]` — returns list of schemas in Anthropic API `tools` format
     - `get_handler(name: str) -> callable` — returns the registered Python handler
     - `register_handler(name: str, handler: callable)` — associates handler with tool name

2. Define tool schemas as Python dicts in `agent/registry.py` (instantiated at module level, registered on import):

   **`allocate_resource`**
   ```json
   {
     "name": "allocate_resource",
     "description": "Allocate a resource (server, license, capacity unit) to a project or operator. Returns allocation ID.",
     "input_schema": {
       "type": "object",
       "properties": {
         "resource_type": {"type": "string", "enum": ["server", "license", "capacity"]},
         "resource_id": {"type": "string"},
         "target_project": {"type": "string"},
         "quantity": {"type": "integer", "minimum": 1},
         "duration_hours": {"type": "integer", "minimum": 1}
       },
       "required": ["resource_type", "resource_id", "target_project", "quantity"]
     }
   }
   ```

   **`cancel_allocation`**
   ```json
   {
     "name": "cancel_allocation",
     "description": "Cancel an existing resource allocation by allocation ID. This is irreversible.",
     "input_schema": {
       "type": "object",
       "properties": {
         "allocation_id": {"type": "string"},
         "reason": {"type": "string"}
       },
       "required": ["allocation_id"]
     }
   }
   ```

   **`link_resources`**
   ```json
   {
     "name": "link_resources",
     "description": "Create a dependency link between two resources or allocations.",
     "input_schema": {
       "type": "object",
       "properties": {
         "source_id": {"type": "string"},
         "target_id": {"type": "string"},
         "link_type": {"type": "string", "enum": ["depends_on", "replaces", "supplements"]}
       },
       "required": ["source_id", "target_id", "link_type"]
     }
   }
   ```

   **`get_resource_status`**
   ```json
   {
     "name": "get_resource_status",
     "description": "Get current status, allocation history, and linked resources for a given resource ID.",
     "input_schema": {
       "type": "object",
       "properties": {
         "resource_id": {"type": "string"}
       },
       "required": ["resource_id"]
     }
   }
   ```

   **`list_allocations`**
   ```json
   {
     "name": "list_allocations",
     "description": "List active allocations, optionally filtered by project, resource type, or operator.",
     "input_schema": {
       "type": "object",
       "properties": {
         "project": {"type": "string"},
         "resource_type": {"type": "string"},
         "status": {"type": "string", "enum": ["active", "cancelled", "all"]}
       }
     }
   }
   ```

3. Write unit tests in `tests/test_dispatcher.py` for schema validation — assert all required schemas load without error and `get_tools_list()` returns 5 items.

---

## Phase 3 — Operation Handlers

**Goal:** Implement the business logic handlers for each MCP tool. Use an in-memory store initially (swappable for a real backend).

### Tasks

1. Create `handlers/base.py`:
   - Class `OperationResult` with fields: `success: bool`, `data: dict`, `error: str | None`
   - All handlers return `OperationResult`

2. Implement `handlers/allocate.py`:
   - Function `handle_allocate(resource_type: str, resource_id: str, target_project: str, quantity: int, duration_hours: int = None) -> OperationResult`
   - Logic:
     - Check resource exists in in-memory `RESOURCE_STORE` dict
     - Check resource is not already fully allocated
     - Generate `allocation_id = f"alloc-{uuid4().hex[:8]}"`
     - Write to `ALLOCATION_STORE[allocation_id]` with status `"active"`, timestamps, all params
     - Return `OperationResult(success=True, data={"allocation_id": ..., "status": "active", ...})`
     - On error: return `OperationResult(success=False, error="...")`

3. Implement `handlers/cancel.py`:
   - Function `handle_cancel(allocation_id: str, reason: str = "") -> OperationResult`
   - Logic: look up `ALLOCATION_STORE[allocation_id]`, set status to `"cancelled"`, record `cancelled_at` and `reason`
   - Return result with previous and new status

4. Implement `handlers/link.py`:
   - Function `handle_link(source_id: str, target_id: str, link_type: str) -> OperationResult`
   - Logic: validate both IDs exist in `ALLOCATION_STORE` or `RESOURCE_STORE`, create link entry in `LINK_STORE`
   - Return `link_id` and full link object

5. Implement `handlers/status.py`:
   - Function `handle_status(resource_id: str) -> OperationResult`
   - Returns full resource record, current allocation if any, and all links

6. Implement `handlers/list_ops.py`:
   - Function `handle_list(project: str = None, resource_type: str = None, status: str = "active") -> OperationResult`
   - Filters `ALLOCATION_STORE` values by provided params; returns list

7. Seed `RESOURCE_STORE` with 20 sample resources (5 servers, 5 licenses, 5 capacity units, 5 misc) so demo works without a real backend.

8. Write `tests/test_handlers.py`:
   - Test full allocate → status → cancel lifecycle
   - Test link creation and retrieval
   - Test cancelling a non-existent allocation returns `success=False`
   - Test list filtering by project and resource_type

---

## Phase 4 — Conversation Manager and Dispatcher

**Goal:** Wire Claude's multi-turn function-calling loop together with the MCP dispatcher and audit logger.

### Tasks

1. Implement `audit/logger.py`:
   - Initialize SQLite DB at `settings.AUDIT_DB_PATH`
   - Create table `audit_log`: `id INTEGER PRIMARY KEY`, `operator_id TEXT`, `tool_name TEXT`, `inputs TEXT (JSON)`, `output TEXT (JSON)`, `success INTEGER`, `timestamp TEXT`, `duration_ms INTEGER`
   - Function `log_tool_call(operator_id, tool_name, inputs, output, success, duration_ms)`
   - Function `get_audit_history(operator_id=None, limit=50) -> list[dict]`

2. Implement `agent/dispatcher.py`:
   - Class `MCPDispatcher`:
     - Constructor: accepts `ToolRegistry` instance
     - Method `dispatch(tool_name: str, tool_use_id: str, inputs: dict, operator_id: str) -> dict`:
       - Validate inputs against tool schema using `jsonschema.validate()`
       - Look up handler via `registry.get_handler(tool_name)`
       - Record start time, call handler, record end time
       - Call `audit_logger.log_tool_call(...)`
       - Return Anthropic `tool_result` block: `{"type": "tool_result", "tool_use_id": ..., "content": json.dumps(result.data) if result.success else result.error}`

3. Implement `agent/conversation.py`:
   - Class `ConversationManager`:
     - Constructor: accepts `settings`, `registry`, `dispatcher`
     - `messages: list[dict]` — sliding window, max `settings.MAX_HISTORY_TURNS * 2` messages
     - Method `chat(user_message: str, operator_id: str) -> str`:
       1. Append `{"role": "user", "content": user_message}` to messages
       2. Call `anthropic.messages.create(model=..., system=system_prompt, messages=messages, tools=registry.get_tools_list(), max_tokens=...)`
       3. If response `stop_reason == "tool_use"`:
          - For each `tool_use` block in response content: call `dispatcher.dispatch(...)`
          - Append assistant message (with tool_use blocks) and all tool_results to messages
          - Loop back to step 2
       4. If response `stop_reason == "end_turn"`: extract text, append to messages, return text
       5. Handle `stop_reason == "max_tokens"` with a graceful truncation message

4. Write `tests/test_conversation.py`:
   - Mock `anthropic.messages.create` to return a `tool_use` block followed by a text response
   - Assert dispatcher is called with correct args
   - Assert final text response is returned
   - Assert message history grows correctly and truncates at max

---

## Phase 5 — CLI and HTTP Interface

**Goal:** Expose the agent via an interactive CLI and an optional FastAPI HTTP endpoint.

### Tasks

1. Implement `cli/chat.py`:
   - `@click.command()` `chat` with options `--operator-id` (default: `"default-operator"`)
   - Loop: `while True: user_input = input("operator> ")`
   - Special commands:
     - `/history` — print last 10 audit log entries for operator
     - `/quit` or `/exit` — break loop
     - `/clear` — reset conversation history
   - All other input: call `conversation_manager.chat(user_input, operator_id)`
   - Print Claude's response with color formatting using click's `click.style()`
   - Entry point: `cli = click.group(); cli.add_command(chat)`

2. Implement `api/main.py`:
   - `POST /chat` endpoint:
     - Request: `{ "message": str, "operator_id": str, "session_id": str }`
     - Session management: maintain one `ConversationManager` per `session_id` in a dict (in-memory, max 100 sessions)
     - Response: `{ "response": str, "tool_calls_made": int, "session_id": str }`
   - `GET /audit` endpoint: returns last 50 audit log entries, protected by `X-Api-Key` header
   - `GET /health` endpoint: returns `{ "status": "ok", "model": settings.CLAUDE_MODEL }`

3. Add `jsonschema==4.22.0` to requirements.txt (used in dispatcher for input validation).

4. Smoke test the full flow:
   ```bash
   python -m cli.chat --operator-id ops-001
   # operator> allocate 2 servers for project alpha
   # (Claude calls allocate_resource, dispatcher runs it, Claude summarizes)
   ```

---

## Phase 6 — Prompt Engineering and Robustness

**Goal:** Harden the system prompt, add edge-case handling, and validate end-to-end behavior across complex multi-step scenarios.

### Tasks

1. Finalize `prompts/system_prompt.txt` with explicit sections:
   - **Role**: "You are an operations management assistant..."
   - **Tool usage rules**: always call `list_allocations` or `get_resource_status` before performing allocations on unknown resource IDs; never invent IDs
   - **Confirmation protocol**: for `cancel_allocation` always echo the allocation details and ask for explicit confirmation before calling the tool
   - **Error handling**: if a tool returns `success: false`, explain the error to the operator and suggest next steps
   - **Multi-step workflows**: describe the expected sequence for "allocate and link" operations

2. Add a `--dry-run` flag to `cli/chat.py`:
   - When set, dispatcher logs calls but does NOT execute handlers
   - Useful for testing prompt behavior without side effects

3. Write end-to-end scenario tests in `tests/test_e2e.py`:
   - Scenario 1: "Allocate server-001 to project alpha then link it to license-005"
     - Assert both `allocate_resource` and `link_resources` are called
   - Scenario 2: "Cancel all allocations for project beta"
     - Assert `list_allocations` called first, then `cancel_allocation` called for each result
   - Scenario 3: Attempt to allocate a non-existent resource ID
     - Assert Claude asks operator to verify or uses `list_allocations` to find valid IDs

4. Run full test suite:
   ```bash
   pytest tests/ -v --asyncio-mode=auto
   ```
