from src.models import Direction
from src.signal_parser import parse_signal

GBPJPY_BUY = """GBPJPY
🔵📊 BUY 214.50

TP: 1️⃣ 214.70
TP: 2️⃣ 215.00
TP: 3️⃣ 215.50
SL: ❌ 213.85"""

GBPJPY_SELL = """GBPJPY
🔴📊 SELL 214.50

TP: 1️⃣ 214.30
TP: 2️⃣ 214.00
TP: 3️⃣ 213.50
SL: ❌ 215.15"""

CHFJPY_BUY = """CHFJPY
🔵📊 BUY 202.95

TP: 1️⃣ 203.15
TP: 2️⃣ 203.45
TP: 3️⃣ 203.95
SL: ❌ 202.30"""


def test_parses_buy_signal():
    sig = parse_signal(GBPJPY_BUY)
    assert sig is not None
    assert sig.symbol == "GBPJPY"
    assert sig.direction is Direction.BUY
    assert sig.entry == 214.50
    assert sig.stop_loss == 213.85
    assert sig.take_profits == [214.70, 215.00, 215.50]


def test_parses_sell_signal():
    sig = parse_signal(GBPJPY_SELL)
    assert sig is not None
    assert sig.direction is Direction.SELL
    assert sig.entry == 214.50
    assert sig.stop_loss == 215.15
    assert sig.take_profits == [214.30, 214.00, 213.50]


def test_parses_different_symbol():
    sig = parse_signal(CHFJPY_BUY)
    assert sig.symbol == "CHFJPY"
    assert sig.take_profits[2] == 203.95


def test_keeps_raw_text():
    sig = parse_signal(GBPJPY_BUY)
    assert sig.raw_text == GBPJPY_BUY


def test_ignores_non_signal_message():
    assert parse_signal("Buenos días traders! Hoy el mercado está volátil 🚀") is None


def test_ignores_message_without_sl():
    text = "GBPJPY\n🔵📊 BUY 214.50\nTP: 1️⃣ 214.70"
    assert parse_signal(text) is None


def test_ignores_empty_message():
    assert parse_signal("") is None
    assert parse_signal(None) is None
