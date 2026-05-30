# src/main.py
from __future__ import annotations

import asyncio
import logging
import os

from telethon import TelegramClient

from src.config import load_config, load_secrets
from src.dedup import SeenStore
from src.file_bridge import FileBridge
from src.notifier import Notifier
from src.pipeline import process_message
from src.telegram_listener import TelegramListener

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("bridge.log")],
)
log = logging.getLogger("main")


def _load_dotenv(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                value = value.strip().strip('"').strip("'")
                os.environ.setdefault(key.strip(), value)


async def amain() -> None:
    _load_dotenv()
    config = load_config()
    secrets = load_secrets()

    bridges = {a.name: FileBridge(a.mailbox_path) for a in config.active_accounts()}
    seen = SeenStore("state/seen.json")

    client = TelegramClient("state/session", secrets.api_id, secrets.api_hash)
    await client.start(phone=secrets.phone)
    log.info("Conectado a Telegram. Escuchando canal: %s", secrets.channel)

    notifier = Notifier(client)

    async def on_message(text: str, mid: int) -> None:
        if seen.seen(mid):
            return
        seen.mark(mid)
        notes: list[str] = []
        # process_message bloquea (polling de archivos) -> a un hilo
        # TODO(MVP): current_open=0 fijo; aún no consulta posiciones reales en MT4.
        outcome = await asyncio.to_thread(
            process_message, text,
            message_id=mid, config=config, bridges=bridges,
            current_open=0, notify=notes.append,
        )
        log.info("Mensaje id=%s -> %s", mid, outcome)
        for note in notes:
            await notifier.send(note)

    listener = TelegramListener(client, secrets.channel, on_message)
    listener.register()

    await notifier.send("🤖 Puente Telegram→MT4 iniciado y escuchando.")
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(amain())
