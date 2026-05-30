# src/telegram_listener.py
from __future__ import annotations

import logging
from typing import Awaitable, Callable

from telethon import TelegramClient, events

log = logging.getLogger(__name__)


class TelegramListener:
    def __init__(self, client: TelegramClient, channel: str,
                 on_message: Callable[[str, int], Awaitable[None]]):
        self._client = client
        self._channel = channel
        self._on_message = on_message

    def register(self) -> None:
        @self._client.on(events.NewMessage(chats=self._channel))
        async def _handler(event):
            text = event.message.message or ""
            mid = event.message.id
            log.info("Mensaje nuevo id=%s", mid)
            try:
                await self._on_message(text, mid)
            except Exception:  # nunca dejar caer el listener por un mensaje
                log.exception("Error procesando mensaje id=%s", mid)
