from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from src.models import OrderRequest, OrderResult


class FileBridge:
    """Puente por archivos hacia un terminal MT4 (un buzón por cuenta)."""

    def __init__(self, mailbox_path: str, timeout_s: float = 10.0, poll_s: float = 0.1):
        self.mailbox = Path(mailbox_path)
        self.commands = self.mailbox / "commands"
        self.responses = self.mailbox / "responses"
        self.timeout_s = timeout_s
        self.poll_s = poll_s
        self.commands.mkdir(parents=True, exist_ok=True)
        self.responses.mkdir(parents=True, exist_ok=True)

    def send(self, req: OrderRequest) -> OrderResult:
        cmd_id = uuid.uuid4().hex
        payload = {
            "id": cmd_id,
            "action": "OPEN",
            "symbol": req.symbol,
            "direction": req.direction.value,
            "lot": req.lot,
            "stop_loss": req.stop_loss,
            "take_profit": req.take_profit,
            "entry_ref": req.entry_ref,
            "tolerance_pips": req.tolerance_pips,
            "comment": req.comment,
        }
        # Escritura atómica: escribir a .tmp y renombrar.
        tmp = self.commands / f"{cmd_id}.json.tmp"
        final = self.commands / f"{cmd_id}.json"
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        tmp.rename(final)

        response_file = self.responses / f"{cmd_id}.json"
        deadline = time.monotonic() + self.timeout_s
        while time.monotonic() < deadline:
            if response_file.exists():
                try:
                    data = json.loads(response_file.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    response_file.unlink(missing_ok=True)
                    return OrderResult(
                        success=False,
                        error="Respuesta del EA ilegible",
                        account=req.account,
                        comment=req.comment,
                    )
                response_file.unlink(missing_ok=True)
                return OrderResult(
                    success=bool(data.get("success")),
                    ticket=data.get("ticket"),
                    price=data.get("price"),
                    error=data.get("error"),
                    account=req.account,
                    comment=req.comment,
                )
            time.sleep(self.poll_s)

        return OrderResult(
            success=False,
            error=f"Timeout: el EA no respondió en {self.timeout_s}s",
            account=req.account,
            comment=req.comment,
        )
