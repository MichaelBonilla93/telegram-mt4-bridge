from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Direction(Enum):
    BUY = "BUY"
    SELL = "SELL"

    @classmethod
    def from_text(cls, text: str) -> "Direction":
        return cls(text.strip().upper())


@dataclass
class Signal:
    symbol: str
    direction: Direction
    entry: float
    stop_loss: float
    take_profits: list[float]
    raw_text: str = ""
    message_id: int | None = None


@dataclass
class Account:
    name: str
    mailbox_path: str
    lot: float
    symbol_suffix: str = ""
    active: bool = True


@dataclass
class OrderRequest:
    account: str
    symbol: str          # ya incluye el sufijo del broker
    direction: Direction
    lot: float
    stop_loss: float
    take_profit: float
    entry_ref: float
    tolerance_pips: float
    comment: str = ""


@dataclass
class OrderResult:
    success: bool
    ticket: int | None = None
    price: float | None = None
    error: str | None = None
    account: str = ""
    comment: str = ""
