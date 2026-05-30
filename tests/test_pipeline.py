from src.config import Config
from src.models import Account, OrderRequest, OrderResult
from src.pipeline import process_message


class FakeBridge:
    def __init__(self):
        self.sent: list[OrderRequest] = []

    def send(self, req: OrderRequest) -> OrderResult:
        self.sent.append(req)
        return OrderResult(success=True, ticket=len(self.sent), price=214.52,
                           account=req.account, comment=req.comment)


GBPJPY_BUY = """GBPJPY
🔵📊 BUY 214.50

TP: 1️⃣ 214.70
TP: 2️⃣ 215.00
TP: 3️⃣ 215.50
SL: ❌ 213.85"""


def _cfg(enabled=True):
    return Config(trading_enabled=enabled, max_open_trades=9, tolerance_pips=20,
                  accounts=[Account("DEMO1", "/tmp/a", lot=0.01)])


def test_valid_signal_sends_three_orders():
    bridge = FakeBridge()
    notes = []
    outcome = process_message(
        GBPJPY_BUY, message_id=1, config=_cfg(),
        bridges={"DEMO1": bridge}, current_open=0, notify=notes.append,
    )
    assert outcome == "executed"
    assert len(bridge.sent) == 3
    assert len(notes) == 1 and "GBPJPY" in notes[0]


def test_non_signal_is_ignored_silently():
    bridge = FakeBridge()
    notes = []
    outcome = process_message(
        "hola traders", message_id=2, config=_cfg(),
        bridges={"DEMO1": bridge}, current_open=0, notify=notes.append,
    )
    assert outcome == "ignored"
    assert bridge.sent == []
    assert notes == []


def test_disabled_trading_discards_and_notifies():
    bridge = FakeBridge()
    notes = []
    outcome = process_message(
        GBPJPY_BUY, message_id=3, config=_cfg(enabled=False),
        bridges={"DEMO1": bridge}, current_open=0, notify=notes.append,
    )
    assert outcome == "discarded"
    assert bridge.sent == []
    assert len(notes) == 1 and "descart" in notes[0].lower()
