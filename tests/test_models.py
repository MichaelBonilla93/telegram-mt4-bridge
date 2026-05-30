from src.models import Direction, Signal, Account, OrderRequest, OrderResult


def test_direction_from_text():
    assert Direction.from_text("BUY") == Direction.BUY
    assert Direction.from_text("sell") == Direction.SELL


def test_signal_holds_three_take_profits():
    sig = Signal(
        symbol="GBPJPY",
        direction=Direction.BUY,
        entry=214.50,
        stop_loss=213.85,
        take_profits=[214.70, 215.00, 215.50],
    )
    assert sig.symbol == "GBPJPY"
    assert sig.direction is Direction.BUY
    assert len(sig.take_profits) == 3
    assert sig.take_profits[0] == 214.70


def test_account_defaults():
    acc = Account(name="DEMO1", mailbox_path="/tmp/mt4", lot=0.01)
    assert acc.symbol_suffix == ""
    assert acc.active is True
