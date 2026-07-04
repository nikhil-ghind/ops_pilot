"""Anthropic tool-use schema definitions for the 8 fintech tools."""

TOOL_SCHEMAS = [
    {
        "name": "get_account",
        "description": "Retrieve account details including balance, status, and flags.",
        "input_schema": {
            "type": "object",
            "properties": {"account_id": {"type": "string", "description": "Account ID (e.g. ACC-001)"}},
            "required": ["account_id"],
        },
    },
    {
        "name": "list_transactions",
        "description": "List recent transactions for an account.",
        "input_schema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string"},
                "limit": {"type": "integer", "default": 20, "description": "Max transactions to return"},
            },
            "required": ["account_id"],
        },
    },
    {
        "name": "flag_transaction",
        "description": "Flag a specific transaction for compliance review.",
        "input_schema": {
            "type": "object",
            "properties": {
                "txn_id": {"type": "string"},
                "reason": {"type": "string", "description": "Reason for flagging"},
            },
            "required": ["txn_id", "reason"],
        },
    },
    {
        "name": "freeze_account",
        "description": "Immediately freeze an account to prevent further transactions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string"},
                "reason": {"type": "string"},
            },
            "required": ["account_id", "reason"],
        },
    },
    {
        "name": "unfreeze_account",
        "description": "Unfreeze an account after analyst review.",
        "input_schema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string"},
                "analyst_id": {"type": "string"},
            },
            "required": ["account_id", "analyst_id"],
        },
    },
    {
        "name": "run_fraud_check",
        "description": "Run a rule-based fraud risk assessment for an account. Returns score and reasons.",
        "input_schema": {
            "type": "object",
            "properties": {"account_id": {"type": "string"}},
            "required": ["account_id"],
        },
    },
    {
        "name": "add_transaction",
        "description": "Record a new debit or credit transaction on an account.",
        "input_schema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string"},
                "amount": {"type": "number"},
                "txn_type": {"type": "string", "enum": ["debit", "credit"]},
                "description": {"type": "string"},
            },
            "required": ["account_id", "amount", "txn_type", "description"],
        },
    },
    {
        "name": "get_alerts",
        "description": "Retrieve active compliance and fraud alerts.",
        "input_schema": {
            "type": "object",
            "properties": {"severity": {"type": "string", "default": "all"}},
        },
    },
]
