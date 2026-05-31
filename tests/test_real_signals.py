"""Casos de regresión con mensajes REALES del canal (descubiertos vía dry-run)."""
from src.config import Config
from src.models import Account
from src.pipeline import process_message
from src.signal_parser import parse_signal

# Señal real #18532: el texto dice "BUY" pero el emoji 🔴, los TPs descendentes y
# el SL por encima de la entrada indican un SELL. Es un error de tipeo del canal.
# Decisión del usuario (2026-05-31): el bot debe DESCARTARLA, no operarla.
XAUUSD_TYPO = "XAUUSD\n🔴📊BUY 4731\n\nTP: 1⃣4729\nTP: 2⃣4726\nTP: 3⃣4721\nSL: ❌4738"


def _cfg():
    return Config(
        trading_enabled=True, max_open_trades=9, tolerance_pips=20,
        accounts=[Account("DEMO1", "/tmp/a", lot=0.01)],
    )


def test_contradictory_signal_parses_as_stated_buy():
    # El parser extrae lo que dice el texto (BUY), sin inventar.
    sig = parse_signal(XAUUSD_TYPO)
    assert sig is not None
    assert sig.symbol == "XAUUSD"
    assert sig.direction.value == "BUY"
    assert sig.entry == 4731
    assert sig.stop_loss == 4738
    assert sig.take_profits == [4729, 4726, 4721]


def test_contradictory_signal_is_discarded_by_risk_guard():
    # BUY con SL por encima de la entrada -> incoherente -> descartada (fail-safe).
    notes = []
    outcome = process_message(
        XAUUSD_TYPO, message_id=18532, config=_cfg(),
        bridges={}, current_open=0, notify=notes.append,
    )
    assert outcome == "discarded"
    assert len(notes) == 1
    assert "incoherente" in notes[0].lower()
