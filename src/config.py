from __future__ import annotations

import os
from dataclasses import dataclass

import yaml

from src.models import Account


@dataclass
class Config:
    trading_enabled: bool
    max_open_trades: int
    tolerance_pips: float
    accounts: list[Account]

    def active_accounts(self) -> list[Account]:
        return [a for a in self.accounts if a.active]


def load_config(path: str = "config.yaml") -> Config:
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    accounts = [
        Account(
            name=a["name"],
            mailbox_path=a["mailbox_path"],
            lot=float(a["lot"]),
            symbol_suffix=a.get("symbol_suffix", ""),
            active=a.get("active", True),
        )
        for a in data.get("accounts", [])
    ]

    return Config(
        trading_enabled=bool(data.get("trading_enabled", True)),
        max_open_trades=int(data.get("max_open_trades", 9)),
        tolerance_pips=float(data.get("tolerance_pips", 20)),
        accounts=accounts,
    )


@dataclass
class Secrets:
    api_id: int
    api_hash: str
    phone: str
    channel: str


def load_secrets() -> Secrets:
    """Lee secretos desde variables de entorno (.env cargado por el caller)."""
    return Secrets(
        api_id=int(os.environ["TG_API_ID"]),
        api_hash=os.environ["TG_API_HASH"],
        phone=os.environ["TG_PHONE"],
        channel=os.environ["TG_CHANNEL"],
    )
