from __future__ import annotations

from src.models import Direction, Signal

ORDERS_PER_SIGNAL = 3  # una por cada TP


def evaluate(
    signal: Signal,
    *,
    trading_enabled: bool,
    max_open_trades: int,
    current_open: int,
) -> tuple[bool, str]:
    """Devuelve (aprobado, motivo). motivo == '' cuando se aprueba."""
    if not trading_enabled:
        return False, "Trading desactivado (kill-switch off)"

    if current_open + ORDERS_PER_SIGNAL > max_open_trades:
        return False, (
            f"Se alcanzaría el máximo de trades "
            f"({current_open}+{ORDERS_PER_SIGNAL} > {max_open_trades})"
        )

    if signal.direction is Direction.BUY:
        if signal.stop_loss >= signal.entry:
            return False, "BUY incoherente: SL por encima o igual a la entrada"
        if any(tp <= signal.entry for tp in signal.take_profits):
            return False, "BUY incoherente: algún TP por debajo o igual a la entrada"
    else:  # SELL
        if signal.stop_loss <= signal.entry:
            return False, "SELL incoherente: SL por debajo o igual a la entrada"
        if any(tp >= signal.entry for tp in signal.take_profits):
            return False, "SELL incoherente: algún TP por encima o igual a la entrada"

    return True, ""
