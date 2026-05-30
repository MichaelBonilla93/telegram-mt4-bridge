from __future__ import annotations

import re

from src.models import Direction, Signal

_NUM = r"(\d+(?:\.\d+)?)"
_DIRECTION_RE = re.compile(rf"\b(BUY|SELL)\b\D*?{_NUM}", re.IGNORECASE)
_SL_RE = re.compile(rf"SL\b\D*?{_NUM}", re.IGNORECASE)
# Asume el formato emoji-tecla del canal (ej. "TP: 1️⃣ 214.70"); omite el ordinal
# con keycap (dígito seguido de ️⃣) para capturar el precio real.
_TP_RE = re.compile(r"TP\b(?:[^\d]|\d[️⃣])+(\d+(?:\.\d+)?)", re.IGNORECASE)
_SYMBOL_RE = re.compile(r"^[A-Z0-9]{3,8}$")


def _find_symbol(lines: list[str]) -> str | None:
    """El símbolo es la primera línea tipo ticker (ej. GBPJPY, XAUUSD, US30)."""
    for line in lines:
        token = line.strip().upper()
        if _SYMBOL_RE.match(token) and not token.startswith(("BUY", "SELL")):
            return token
    return None


def parse_signal(text: str | None) -> Signal | None:
    """Convierte el texto de un mensaje en un Signal, o None si no es señal válida."""
    if not text or not text.strip():
        return None

    lines = [ln for ln in text.splitlines() if ln.strip()]

    dir_match = _DIRECTION_RE.search(text)
    sl_match = _SL_RE.search(text)
    tps = [float(m) for m in _TP_RE.findall(text)]
    symbol = _find_symbol(lines)

    # Una señal válida necesita: símbolo, dirección+entrada, SL y al menos 3 TP.
    if not (symbol and dir_match and sl_match and len(tps) >= 3):
        return None

    direction = Direction.from_text(dir_match.group(1))
    entry = float(dir_match.group(2))
    stop_loss = float(sl_match.group(1))

    return Signal(
        symbol=symbol,
        direction=direction,
        entry=entry,
        stop_loss=stop_loss,
        take_profits=tps[:3],
        raw_text=text,
    )
