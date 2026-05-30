import json
import threading
import time
from pathlib import Path

from src.file_bridge import FileBridge
from src.models import Direction, OrderRequest

REQ = OrderRequest(
    account="DEMO1", symbol="GBPJPY", direction=Direction.BUY, lot=0.01,
    stop_loss=213.85, take_profit=214.70, entry_ref=214.50,
    tolerance_pips=20, comment="TG TP1",
)


def _fake_ea(mailbox: Path, ticket: int = 5001):
    """Simula al EA: lee el comando, escribe respuesta, borra comando."""
    commands = mailbox / "commands"
    responses = mailbox / "responses"
    for _ in range(50):
        files = list(commands.glob("*.json"))
        if files:
            cmd_file = files[0]
            cmd = json.loads(cmd_file.read_text())
            (responses / cmd_file.name).write_text(json.dumps({
                "id": cmd["id"], "success": True,
                "ticket": ticket, "price": 214.52, "error": None,
            }))
            cmd_file.unlink()
            return
        time.sleep(0.02)


def test_command_roundtrip(tmp_path):
    bridge = FileBridge(str(tmp_path), timeout_s=3)
    t = threading.Thread(target=_fake_ea, args=(tmp_path,))
    t.start()

    result = bridge.send(REQ)
    t.join()

    assert result.success is True
    assert result.ticket == 5001
    assert result.price == 214.52
    assert result.account == "DEMO1"
    assert result.comment == "TG TP1"


def test_command_file_has_expected_fields(tmp_path):
    bridge = FileBridge(str(tmp_path), timeout_s=1)
    # No arrancamos EA: el comando queda escrito y luego da timeout
    bridge.send(REQ)  # devolverá error por timeout
    written = list((tmp_path / "commands").glob("*.json"))
    assert len(written) == 1
    cmd = json.loads(written[0].read_text())
    assert cmd["action"] == "OPEN"
    assert cmd["symbol"] == "GBPJPY"
    assert cmd["direction"] == "BUY"
    assert cmd["lot"] == 0.01
    assert cmd["stop_loss"] == 213.85
    assert cmd["take_profit"] == 214.70
    assert cmd["tolerance_pips"] == 20


def test_timeout_returns_error(tmp_path):
    bridge = FileBridge(str(tmp_path), timeout_s=0.3)
    result = bridge.send(REQ)
    assert result.success is False
    assert "timeout" in result.error.lower()
