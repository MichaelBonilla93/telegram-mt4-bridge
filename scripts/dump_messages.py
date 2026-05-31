"""Utilidad de depuración: imprime el texto crudo de mensajes por id.

Uso:
    python scripts/dump_messages.py 18532 18538 18596
"""
from __future__ import annotations

import asyncio
import os
import sys

# Permite ejecutar el script directamente (añade la raíz del proyecto al path).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telethon import TelegramClient

from src.dry_run import resolve_channel
from src.main import _load_dotenv


async def run(ids: list[int]) -> None:
    _load_dotenv()
    client = TelegramClient(
        "state/session", int(os.environ["TG_API_ID"]), os.environ["TG_API_HASH"]
    )
    await client.start(phone=os.environ["TG_PHONE"])
    entity = await resolve_channel(client, os.environ["TG_CHANNEL"])
    for mid in ids:
        msg = await client.get_messages(entity, ids=mid)
        print(f"==== #{mid} ====")
        print(repr(msg.message if msg else None))
        print()
    await client.disconnect()


if __name__ == "__main__":
    ids = [int(a) for a in sys.argv[1:]] or [18532, 18538, 18596]
    asyncio.run(run(ids))
