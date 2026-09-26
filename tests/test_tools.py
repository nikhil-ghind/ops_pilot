from src.tools.fintech_tools import (get_account, freeze_account, unfreeze_account,
                                      run_fraud_check, add_transaction, flag_transaction)


def test_get_account_found():
    r = get_account("ACC-001")
    assert r["owner"] == "Alice Wong"
    assert "balance" in r


def test_get_account_not_found():
    r = get_account("ACC-999")
    assert "error" in r


def test_freeze_unfreeze():
    freeze_account("ACC-002", "test_freeze")
    r = get_account("ACC-002")
    assert r["status"] == "frozen"
    unfreeze_account("ACC-002", "analyst_1")
    r = get_account("ACC-002")
    assert r["status"] == "active"


def test_add_transaction_blocked_on_frozen():
    freeze_account("ACC-004", "test")
    r = add_transaction("ACC-004", 100.0, "debit", "test payment")
    assert "error" in r
    unfreeze_account("ACC-004", "analyst_1")


def test_fraud_check_low_risk():
    r = run_fraud_check("ACC-001")
    assert "risk_level" in r
    assert r["risk_level"] in {"LOW", "MEDIUM", "HIGH"}
