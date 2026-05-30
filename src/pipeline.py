from __future__ import annotations

from typing import Callable

from src.config import Config
from src.file_bridge import FileBridge
from src.models import OrderResult
from src.notifier import format_discarded, format_executed
from src.order_router import build_orders
from src.risk_guard import evaluate
from src.signal_parser import parse_signal


def process_message(
    text: str,
    *,
    message_id: int,
    config: Config,
    bridges: dict[str, FileBridge],
    current_open: int,
    notify: Callable[[str], None],
) -> str:
    """Procesa un mensaje. Devuelve 'ignored' | 'discarded' | 'executed'."""
    signal = parse_signal(text)
    if signal is None:
        return "ignored"
    signal.message_id = message_id

    ok, reason = evaluate(
        signal,
        trading_enabled=config.trading_enabled,
        max_open_trades=config.max_open_trades,
        current_open=current_open,
    )
    if not ok:
        notify(format_discarded(signal, reason))
        return "discarded"

    accounts = config.active_accounts()
    orders = build_orders(signal, accounts, tolerance_pips=config.tolerance_pips)

    results = []
    for order in orders:
        bridge = bridges.get(order.account)
        if bridge is None:
            results.append(OrderResult(
                success=False,
                error=f"Sin puente configurado para la cuenta {order.account}",
                account=order.account,
                comment=order.comment,
            ))
            continue
        results.append(bridge.send(order))

    notify(format_executed(signal, results))
    return "executed"
