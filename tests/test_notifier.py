from src.models import Direction, OrderResult, Signal
from src.notifier import format_executed, format_discarded

BUY = Signal("GBPJPY", Direction.BUY, 214.50, 213.85, [214.70, 215.00, 215.50])


def test_format_discarded_includes_reason():
    msg = format_discarded(BUY, "Trading desactivado (kill-switch off)")
    assert "GBPJPY" in msg
    assert "descart" in msg.lower()
    assert "kill-switch" in msg.lower()


def test_format_executed_lists_tickets_and_failures():
    results = [
        OrderResult(success=True, ticket=1, price=214.52, account="DEMO1", comment="TG TP1"),
        OrderResult(success=True, ticket=2, price=214.52, account="DEMO1", comment="TG TP2"),
        OrderResult(success=False, error="price moved", account="DEMO1", comment="TG TP3"),
    ]
    msg = format_executed(BUY, results)
    assert "GBPJPY" in msg
    assert "BUY" in msg
    assert "#1" in msg and "#2" in msg
    assert "TP3" in msg
    assert "price moved" in msg
    assert "2/3" in msg  # 2 de 3 exitosas
