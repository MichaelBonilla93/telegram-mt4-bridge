from __future__ import annotations

from src.models import OrderResult, Signal


def format_discarded(signal: Signal, reason: str) -> str:
    return (
        f"⚠️ Señal descartada — {signal.symbol} {signal.direction.value} "
        f"@ {signal.entry}\nMotivo: {reason}"
    )


def format_executed(signal: Signal, results: list[OrderResult]) -> str:
    ok = [r for r in results if r.success]
    lines = [
        f"✅ {signal.symbol} {signal.direction.value} @ {signal.entry} "
        f"| SL {signal.stop_loss}",
        f"Ejecutadas {len(ok)}/{len(results)}:",
    ]
    for r in results:
        if r.success:
            lines.append(f"  • {r.account} {r.comment}: #{r.ticket} @ {r.price}")
        else:
            lines.append(f"  • {r.account} {r.comment}: ❌ {r.error}")
    return "\n".join(lines)


class Notifier:
    """Envía mensajes a Mensajes Guardados usando un cliente Telethon."""

    def __init__(self, client):
        self._client = client

    async def send(self, text: str) -> None:
        # 'me' = chat de Mensajes Guardados del propio usuario
        await self._client.send_message("me", text)
