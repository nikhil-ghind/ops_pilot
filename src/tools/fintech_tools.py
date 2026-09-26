"""MCP-style fintech operations tools for OpsPilot."""
from __future__ import annotations
import json
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


# ── In-memory ledger (swap for real DB in production) ──────────────────────

_ACCOUNTS: dict[str, dict] = {
    "ACC-001": {"owner": "Alice Wong",    "balance": 42_500.00, "status": "active",  "flags": []},
    "ACC-002": {"owner": "Bob Marchetti", "balance":  3_200.00, "status": "active",  "flags": []},
    "ACC-003": {"owner": "Carol Diaz",    "balance": 15_900.00, "status": "frozen",  "flags": ["suspicious_activity"]},
    "ACC-004": {"owner": "Dave Kim",      "balance":   870.00,  "status": "active",  "flags": []},
}

_TRANSACTIONS: list[dict] = []
_ALERTS: list[dict] = []

_TXN_ID = iter(range(1000, 9999))


def _now() -> str:
    return datetime.utcnow().isoformat()


# ── Tool implementations ────────────────────────────────────────────────────

def get_account(account_id: str) -> dict[str, Any]:
    """Return account details or an error dict."""
    acc = _ACCOUNTS.get(account_id.upper())
    if not acc:
        return {"error": f"Account {account_id} not found"}
    return {"account_id": account_id, **acc}


def list_transactions(account_id: str, limit: int = 20) -> dict[str, Any]:
    """Return recent transactions for an account."""
    txns = [t for t in _TRANSACTIONS if t["account_id"] == account_id.upper()]
    return {"account_id": account_id, "transactions": txns[-limit:], "count": len(txns)}


def flag_transaction(txn_id: str, reason: str) -> dict[str, Any]:
    """Flag a transaction for review."""
    for t in _TRANSACTIONS:
        if t["txn_id"] == txn_id:
            t["flagged"] = True
            t["flag_reason"] = reason
            _ALERTS.append({"type": "txn_flag", "txn_id": txn_id,
                             "reason": reason, "ts": _now()})
            return {"status": "flagged", "txn_id": txn_id, "reason": reason}
    return {"error": f"Transaction {txn_id} not found"}


def freeze_account(account_id: str, reason: str) -> dict[str, Any]:
    """Freeze an account immediately."""
    acc = _ACCOUNTS.get(account_id.upper())
    if not acc:
        return {"error": f"Account {account_id} not found"}
    acc["status"] = "frozen"
    acc["flags"].append(reason)
    _ALERTS.append({"type": "account_freeze", "account_id": account_id,
                     "reason": reason, "ts": _now()})
    return {"status": "frozen", "account_id": account_id, "reason": reason}


def unfreeze_account(account_id: str, analyst_id: str) -> dict[str, Any]:
    """Unfreeze an account after review."""
    acc = _ACCOUNTS.get(account_id.upper())
    if not acc:
        return {"error": f"Account {account_id} not found"}
    acc["status"] = "active"
    return {"status": "active", "account_id": account_id,
            "unfrozen_by": analyst_id, "ts": _now()}


def run_fraud_check(account_id: str) -> dict[str, Any]:
    """Run a rule-based fraud risk score for an account."""
    acc = _ACCOUNTS.get(account_id.upper())
    if not acc:
        return {"error": f"Account {account_id} not found"}
    txns = [t for t in _TRANSACTIONS if t["account_id"] == account_id.upper()]

    score = 0
    reasons = []
    if acc["status"] == "frozen":
        score += 40; reasons.append("account currently frozen")
    if acc["flags"]:
        score += 20 * len(acc["flags"]); reasons.append(f"existing flags: {acc['flags']}")
    large = [t for t in txns[-10:] if t.get("amount", 0) > 5000]
    if large:
        score += 15 * len(large); reasons.append(f"{len(large)} large transactions in last 10")
    velocity = len([t for t in txns if t.get("ts", "") > (datetime.utcnow() - timedelta(hours=1)).isoformat()])
    if velocity > 10:
        score += 25; reasons.append(f"high velocity: {velocity} txns in last hour")

    risk = "HIGH" if score >= 60 else "MEDIUM" if score >= 30 else "LOW"
    return {"account_id": account_id, "risk_score": min(100, score),
            "risk_level": risk, "reasons": reasons}


def add_transaction(account_id: str, amount: float,
                     txn_type: str, description: str) -> dict[str, Any]:
    """Record a new transaction."""
    acc = _ACCOUNTS.get(account_id.upper())
    if not acc:
        return {"error": f"Account {account_id} not found"}
    if acc["status"] == "frozen":
        return {"error": f"Account {account_id} is frozen — transaction blocked"}
    txn_id = f"TXN-{next(_TXN_ID)}"
    txn = {"txn_id": txn_id, "account_id": account_id.upper(),
           "amount": amount, "type": txn_type,
           "description": description, "flagged": False, "ts": _now()}
    _TRANSACTIONS.append(txn)
    if txn_type == "debit":
        acc["balance"] -= amount
    else:
        acc["balance"] += amount
    return txn


def get_alerts(severity: str = "all") -> dict[str, Any]:
    """Return all active alerts, optionally filtered by severity."""
    alerts = _ALERTS if severity == "all" else [a for a in _ALERTS if a.get("severity") == severity]
    return {"alerts": alerts, "count": len(alerts)}


TOOL_MAP = {
    "get_account":        get_account,
    "list_transactions":  list_transactions,
    "flag_transaction":   flag_transaction,
    "freeze_account":     freeze_account,
    "unfreeze_account":   unfreeze_account,
    "run_fraud_check":    run_fraud_check,
    "add_transaction":    add_transaction,
    "get_alerts":         get_alerts,
}
