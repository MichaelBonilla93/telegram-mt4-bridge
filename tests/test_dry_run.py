from src.config import Config
from src.dry_run import DryRunBridge, analyze, format_line
from src.models import Account, Direction, OrderRequest

GBPJPY_BUY = """GBPJPY
🔵📊 BUY 214.50

TP: 1️⃣ 214.70
TP: 2️⃣ 215.00
TP: 3️⃣ 215.50
SL: ❌ 213.85"""


def _cfg(enabled=True):
    return Config(
        trading_enabled=enabled, max_open_trades=9, tolerance_pips=20,
        accounts=[Account("DEMO1", "/tmp/a", lot=0.01)],
    )


def test_dry_run_bridge_records_and_never_fails():
    bridge = DryRunBridge()
    req = OrderRequest(
        account="DEMO1", symbol="GBPJPY", direction=Direction.BUY, lot=0.01,
        stop_loss=213.85, take_profit=214.70, entry_ref=214.50,
        tolerance_pips=20, comment="TG TP1",
    )
    res = bridge.send(req)
    assert res.success is True
    assert res.account == "DEMO1"
    assert bridge.sent == [req]


def test_analyze_valid_signal_simulates_three_orders():
    result = analyze(GBPJPY_BUY, message_id=1, config=_cfg())
    assert result.outcome == "executed"
    assert len(result.orders) == 3
    assert [o.take_profit for o in result.orders] == [214.70, 215.00, 215.50]
    assert all(o.account == "DEMO1" for o in result.orders)
    assert len(result.notes) == 1


def test_analyze_ignores_non_signal():
    result = analyze("Buenos días traders 🚀", message_id=2, config=_cfg())
    assert result.outcome == "ignored"
    assert result.orders == []
    assert result.notes == []


def test_analyze_discarded_when_trading_disabled():
    result = analyze(GBPJPY_BUY, message_id=3, config=_cfg(enabled=False))
    assert result.outcome == "discarded"
    assert result.orders == []
    assert len(result.notes) == 1


def test_analyze_does_not_touch_real_bridge():
    # No debe escribir nada a disco: usa DryRunBridge interno.
    result = analyze(GBPJPY_BUY, message_id=4, config=_cfg())
    assert all(isinstance(o, OrderRequest) for o in result.orders)


def test_format_line_marks_outcomes():
    executed = analyze(GBPJPY_BUY, message_id=10, config=_cfg())
    line = format_line(message_id=10, text=GBPJPY_BUY, result=executed)
    assert "10" in line
    assert "GBPJPY" in line
    assert "3" in line  # 3 órdenes simuladas

    ignored = analyze("hola", message_id=11, config=_cfg())
    line2 = format_line(message_id=11, text="hola", result=ignored)
    assert "ignored" in line2.lower() or "ignorad" in line2.lower()
