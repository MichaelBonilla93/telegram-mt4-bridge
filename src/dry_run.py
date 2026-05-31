"""Modo dry-run de solo lectura.

Conecta a Telegram, trae los últimos N mensajes del canal y los pasa por el
pipeline completo (parser + risk_guard + order_router) usando un bridge SIMULADO
que NO escribe a MT4. Sirve para validar el parser contra mensajes reales y ver
qué órdenes se enviarían, sin abrir ningún trade.

Uso:
    python -m src.dry_run [N]      # N = cantidad de mensajes (por defecto 50)
"""
from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass, field

from src.config import Config, load_config, load_secrets
from src.main import _load_dotenv
from src.models import OrderRequest, OrderResult
from src.pipeline import process_message


class DryRunBridge:
    """Bridge simulado: registra la orden y devuelve éxito ficticio, sin tocar MT4.

    La tolerancia de pips NO se simula aquí (en producción la valida el EA con el
    precio en vivo); este modo valida parseo, guardas de riesgo y ruteo.
    """

    def __init__(self) -> None:
        self.sent: list[OrderRequest] = []

    def send(self, req: OrderRequest) -> OrderResult:
        self.sent.append(req)
        return OrderResult(
            success=True,
            ticket=0,
            price=req.entry_ref,
            account=req.account,
            comment=req.comment,
        )


@dataclass
class DryRunResult:
    outcome: str  # 'ignored' | 'discarded' | 'executed'
    orders: list[OrderRequest] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def analyze(text: str, *, message_id: int, config: Config) -> DryRunResult:
    """Procesa un mensaje por el pipeline con bridges simulados (sin I/O a MT4)."""
    bridges = {a.name: DryRunBridge() for a in config.active_accounts()}
    notes: list[str] = []
    outcome = process_message(
        text,
        message_id=message_id,
        config=config,
        bridges=bridges,
        current_open=0,
        notify=notes.append,
    )
    orders = [o for b in bridges.values() for o in b.sent]
    return DryRunResult(outcome=outcome, orders=orders, notes=notes)


def format_line(*, message_id: int, text: str, result: DryRunResult) -> str:
    """Línea de resumen por mensaje para la consola."""
    first = (text or "").strip().splitlines()
    preview = first[0] if first else "(vacío)"
    if result.outcome == "executed":
        return f"[#{message_id}] ✅ EXECUTED ({len(result.orders)} órdenes) — {preview}"
    if result.outcome == "discarded":
        motivo = result.notes[0] if result.notes else ""
        return f"[#{message_id}] ⚠️  DISCARDED — {preview}\n        {motivo}"
    return f"[#{message_id}] ·  ignored — {preview}"


async def run(limit: int = 50) -> dict:
    """Trae los últimos `limit` mensajes del canal y los analiza. Devuelve conteos."""
    from telethon import TelegramClient

    _load_dotenv()
    config = load_config()
    secrets = load_secrets()

    client = TelegramClient("state/session", secrets.api_id, secrets.api_hash)
    await client.start(phone=secrets.phone)
    print(f"Conectado. Trayendo últimos {limit} mensajes de: {secrets.channel}\n")

    messages = await client.get_messages(secrets.channel, limit=limit)
    counts = {"ignored": 0, "discarded": 0, "executed": 0}

    for msg in reversed(list(messages)):  # del más viejo al más nuevo
        text = msg.message or ""
        result = analyze(text, message_id=msg.id, config=config)
        counts[result.outcome] += 1
        print(format_line(message_id=msg.id, text=text, result=result))
        for order in result.orders:
            print(
                f"        → {order.account} {order.comment}: {order.symbol} "
                f"{order.direction.value} {order.lot} SL {order.stop_loss} "
                f"TP {order.take_profit}"
            )

    await client.disconnect()
    print(
        f"\nResumen: {counts['executed']} señales, "
        f"{counts['discarded']} descartadas, {counts['ignored']} ignoradas "
        f"(de {len(messages)} mensajes). NINGÚN trade abierto (dry-run)."
    )
    return counts


def _main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    asyncio.run(run(limit))


if __name__ == "__main__":
    _main()
