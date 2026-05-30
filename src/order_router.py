from __future__ import annotations

from src.models import Account, OrderRequest, Signal


def build_orders(
    signal: Signal,
    accounts: list[Account],
    *,
    tolerance_pips: float,
) -> list[OrderRequest]:
    """Genera 3 OrderRequest (TP1/TP2/TP3) por cada cuenta dada."""
    orders: list[OrderRequest] = []
    for account in accounts:
        symbol = f"{signal.symbol}{account.symbol_suffix}"
        for i, tp in enumerate(signal.take_profits, start=1):
            orders.append(
                OrderRequest(
                    account=account.name,
                    symbol=symbol,
                    direction=signal.direction,
                    lot=account.lot,
                    stop_loss=signal.stop_loss,
                    take_profit=tp,
                    entry_ref=signal.entry,
                    tolerance_pips=tolerance_pips,
                    comment=f"TG TP{i}",
                )
            )
    return orders
