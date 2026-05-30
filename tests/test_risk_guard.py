from src.models import Direction, Signal
from src.risk_guard import evaluate

BUY = Signal("GBPJPY", Direction.BUY, 214.50, 213.85, [214.70, 215.00, 215.50])
SELL = Signal("GBPJPY", Direction.SELL, 214.50, 215.15, [214.30, 214.00, 213.50])


def test_rejects_when_trading_disabled():
    ok, reason = evaluate(BUY, trading_enabled=False, max_open_trades=9, current_open=0)
    assert ok is False
    assert "desactivado" in reason.lower()


def test_rejects_when_max_trades_reached():
    # 3 nuevas órdenes no caben si ya hay 7 y el máx es 9
    ok, reason = evaluate(BUY, trading_enabled=True, max_open_trades=9, current_open=7)
    assert ok is False
    assert "máximo" in reason.lower()


def test_rejects_buy_with_sl_above_entry():
    bad = Signal("GBPJPY", Direction.BUY, 214.50, 215.00, [214.70, 215.00, 215.50])
    ok, reason = evaluate(bad, trading_enabled=True, max_open_trades=9, current_open=0)
    assert ok is False
    assert "sl" in reason.lower()


def test_rejects_sell_with_sl_below_entry():
    bad = Signal("GBPJPY", Direction.SELL, 214.50, 213.00, [214.30, 214.00, 213.50])
    ok, reason = evaluate(bad, trading_enabled=True, max_open_trades=9, current_open=0)
    assert ok is False


def test_accepts_valid_buy():
    ok, reason = evaluate(BUY, trading_enabled=True, max_open_trades=9, current_open=0)
    assert ok is True
    assert reason == ""


def test_accepts_valid_sell():
    ok, _ = evaluate(SELL, trading_enabled=True, max_open_trades=9, current_open=0)
    assert ok is True
