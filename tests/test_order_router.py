from src.models import Account, Direction, Signal
from src.order_router import build_orders

BUY = Signal("GBPJPY", Direction.BUY, 214.50, 213.85, [214.70, 215.00, 215.50])


def test_builds_three_orders_per_account():
    accounts = [Account("DEMO1", "/tmp/a", lot=0.01)]
    orders = build_orders(BUY, accounts, tolerance_pips=20)
    assert len(orders) == 3
    assert [o.take_profit for o in orders] == [214.70, 215.00, 215.50]
    assert all(o.stop_loss == 213.85 for o in orders)
    assert all(o.lot == 0.01 for o in orders)
    assert all(o.direction is Direction.BUY for o in orders)
    assert all(o.entry_ref == 214.50 for o in orders)
    assert all(o.tolerance_pips == 20 for o in orders)


def test_applies_symbol_suffix_per_account():
    accounts = [Account("DEMO2", "/tmp/b", lot=0.02, symbol_suffix=".r")]
    orders = build_orders(BUY, accounts, tolerance_pips=20)
    assert all(o.symbol == "GBPJPY.r" for o in orders)
    assert all(o.lot == 0.02 for o in orders)


def test_fans_out_to_multiple_accounts():
    accounts = [
        Account("DEMO1", "/tmp/a", lot=0.01),
        Account("DEMO2", "/tmp/b", lot=0.02, symbol_suffix=".r"),
    ]
    orders = build_orders(BUY, accounts, tolerance_pips=20)
    assert len(orders) == 6  # 3 TP x 2 cuentas
    assert {o.account for o in orders} == {"DEMO1", "DEMO2"}


def test_comment_marks_tp_level():
    accounts = [Account("DEMO1", "/tmp/a", lot=0.01)]
    orders = build_orders(BUY, accounts, tolerance_pips=20)
    assert orders[0].comment == "TG TP1"
    assert orders[2].comment == "TG TP3"
