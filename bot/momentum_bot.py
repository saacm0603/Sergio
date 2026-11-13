"""Bot de rebalanceo mensual para Alpaca — Estrategia 1 (momentum en ETFs).

Uso:
    python bot/momentum_bot.py                 # simulación: muestra el plan, NO envía órdenes
    python bot/momentum_bot.py --execute       # envía órdenes (solo si hoy toca rebalancear)
    python bot/momentum_bot.py --execute --force   # rebalancea ahora aunque no sea fin de mes

Variables de entorno:
    ALPACA_API_KEY, ALPACA_SECRET_KEY   claves de la cuenta (obligatorias)
    ALPACA_PAPER        "true" (por defecto) = cuenta paper. Para dinero real: "false".
    BOT_CAPITAL         dólares que gestiona el bot (por defecto: equity menos posiciones ajenas
                        a la estrategia, que el bot nunca toca)
    ALPACA_DATA_FEED    "iex" (gratis, por defecto) o "sip" (Algo Trader Plus)
    MIN_TRADE_USD       no operar diferencias menores a esto (por defecto 25)

Cuándo opera: el último día hábil del mes, entre 120 y 5 minutos antes del cierre.
Solo opera una vez por mes (si ya hay órdenes "tsmom-AAAAMM" este mes, no hace nada).
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from strategy import CASH, UNIVERSE, momentum_table, target_weights  # noqa: E402

NY = ZoneInfo("America/New_York")
CASH_BUFFER = 0.01          # deja 1% sin invertir para redondeos / movimientos de precio
WINDOW_MIN, WINDOW_MAX = 5, 120  # minutos antes del cierre en los que se permite operar


@dataclass
class Order:
    symbol: str
    side: str          # "buy" | "sell"
    notional: float    # dólares
    close_all: bool = False


def plan_orders(capital: float, positions: dict[str, float], weights: pd.Series,
                min_trade: float = 25.0) -> list[Order]:
    """Función pura: diferencia entre posiciones actuales (valor de mercado $) y objetivo.
    Ventas primero (liberan efectivo), luego compras."""
    investable = capital * (1 - CASH_BUFFER)
    sells, buys = [], []
    for sym in UNIVERSE + [CASH]:
        target = investable * float(weights.get(sym, 0.0))
        current = positions.get(sym, 0.0)
        delta = target - current
        if target < 1e-9 and current > 0:
            sells.append(Order(sym, "sell", round(current, 2), close_all=True))
        elif delta <= -min_trade:
            sells.append(Order(sym, "sell", round(-delta, 2)))
        elif delta >= min_trade:
            buys.append(Order(sym, "buy", round(delta, 2)))
    return sells + buys


def should_trade_today(trading, now: datetime) -> tuple[bool, str]:
    from alpaca.trading.requests import GetCalendarRequest
    clock = trading.get_clock()
    if not clock.is_open:
        return False, "el mercado está cerrado"
    today = now.astimezone(NY).date()
    cal = trading.get_calendar(GetCalendarRequest(start=today, end=today + timedelta(days=12)))
    days = [c.date for c in cal]
    if not days or days[0] != today:
        return False, "hoy no es día hábil"
    nxt = days[1] if len(days) > 1 else None
    if nxt is not None and nxt.month == today.month:
        return False, f"hoy no es el último día hábil del mes (el siguiente es {nxt})"
    mins = (clock.next_close - clock.timestamp).total_seconds() / 60
    if not (WINDOW_MIN <= mins <= WINDOW_MAX):
        return False, f"faltan {mins:.0f} min para el cierre (ventana {WINDOW_MAX}-{WINDOW_MIN} min)"
    return True, f"último día hábil del mes, faltan {mins:.0f} min para el cierre"


def already_rebalanced(trading, now: datetime) -> bool:
    from alpaca.trading.enums import QueryOrderStatus
    from alpaca.trading.requests import GetOrdersRequest
    month_start = now.astimezone(NY).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    orders = trading.get_orders(GetOrdersRequest(status=QueryOrderStatus.ALL,
                                                 after=month_start, limit=500))
    tag = f"tsmom-{now.astimezone(NY):%Y%m}"
    return any((o.client_order_id or "").startswith(tag) for o in orders)


def load_closes(data_client, feed: str) -> pd.DataFrame:
    from alpaca.data.enums import Adjustment, DataFeed
    from alpaca.data.requests import StockBarsRequest, StockLatestTradeRequest
    from alpaca.data.timeframe import TimeFrame
    syms = UNIVERSE + [CASH]
    now = datetime.now(tz=NY)
    end = now - timedelta(minutes=16) if feed == "sip" else None  # SIP gratis solo con >15 min
    bars = data_client.get_stock_bars(StockBarsRequest(
        symbol_or_symbols=syms, timeframe=TimeFrame.Day, start=now - timedelta(days=430),
        end=end, adjustment=Adjustment.ALL, feed=DataFeed(feed),
    )).df
    closes = bars["close"].unstack(level=0)
    closes.index = pd.to_datetime(closes.index).tz_convert(NY).tz_localize(None).normalize()
    # Precio más reciente como cierre de hoy (el rebalanceo se hace minutos antes del cierre)
    latest = data_client.get_stock_latest_trade(StockLatestTradeRequest(
        symbol_or_symbols=syms, feed=DataFeed(feed)))
    today = pd.Timestamp(now.date())
    for s, t in latest.items():
        closes.loc[today, s] = float(t.price)
    return closes.sort_index()


def wait_for_fills(trading, order_ids: list, timeout_s: int = 90) -> None:
    deadline = time.time() + timeout_s
    pending = set(order_ids)
    while pending and time.time() < deadline:
        for oid in list(pending):
            o = trading.get_order_by_id(oid)
            if getattr(o.status, "value", str(o.status)).lower() in ("filled", "canceled", "rejected", "expired"):
                pending.discard(oid)
        if pending:
            time.sleep(3)
    if pending:
        print(f"⚠️  {len(pending)} ventas sin completar tras {timeout_s}s; las compras se ajustan al efectivo disponible")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--execute", action="store_true", help="enviar órdenes (sin esto: solo simulación)")
    ap.add_argument("--force", action="store_true", help="ignorar la comprobación de fin de mes")
    args = ap.parse_args()

    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.trading.client import TradingClient
    from alpaca.trading.enums import OrderSide, TimeInForce
    from alpaca.trading.requests import MarketOrderRequest

    key, secret = os.environ.get("ALPACA_API_KEY"), os.environ.get("ALPACA_SECRET_KEY")
    if not key or not secret:
        print("Faltan ALPACA_API_KEY / ALPACA_SECRET_KEY"); return 2
    paper = os.environ.get("ALPACA_PAPER", "true").lower() != "false"
    feed = os.environ.get("ALPACA_DATA_FEED", "iex").lower()
    min_trade = float(os.environ.get("MIN_TRADE_USD", "25"))

    trading = TradingClient(key, secret, paper=paper)
    data = StockHistoricalDataClient(key, secret)
    now = datetime.now(tz=NY)
    print(f"== Bot momentum ETFs | {now:%Y-%m-%d %H:%M} ET | cuenta {'PAPER' if paper else '⚠️ REAL'} "
          f"| {'EJECUCIÓN' if args.execute else 'SIMULACIÓN'} ==")

    ok, reason = should_trade_today(trading, now)
    print(f"¿Toca rebalancear? {'sí' if ok else 'no'} — {reason}")
    if not ok and not args.force:
        return 0
    if args.execute and already_rebalanced(trading, now):
        print("Ya se rebalanceó este mes (hay órdenes tsmom-*). Nada que hacer."); return 0

    closes = load_closes(data, feed)
    weights = target_weights(closes)
    print("\nSeñal:\n" + momentum_table(closes).to_string(float_format=lambda v: f"{v:8.2%}"))
    print(f"{CASH:>4}  peso {weights[CASH]:.2%}  (efectivo / bonos cortos)")

    account = trading.get_account()
    equity = float(account.equity)
    positions = {p.symbol: float(p.market_value) for p in trading.get_all_positions()}
    others = sorted(set(positions) - set(UNIVERSE) - {CASH})
    others_value = sum(positions[s] for s in others)
    if others:
        print(f"ℹ️  Posiciones fuera de la estrategia (no se tocan): {', '.join(others)} "
              f"(${others_value:,.2f})")
    available = equity - others_value
    capital = min(float(os.environ.get("BOT_CAPITAL") or available), available)
    orders = plan_orders(capital, positions, weights, min_trade)

    print(f"\nCapital gestionado: ${capital:,.2f} (equity ${equity:,.2f})")
    if not orders:
        print("La cartera ya está en sus pesos objetivo."); return 0
    print("Órdenes planificadas:")
    for o in orders:
        print(f"  {o.side.upper():4} {o.symbol:4} ${o.notional:>11,.2f}{'  (cerrar posición)' if o.close_all else ''}")
    if not args.execute:
        print("\nSimulación: no se envió ninguna orden. Usa --execute para operar."); return 0

    tag = f"tsmom-{now:%Y%m}"
    sell_ids = []
    for o in [o for o in orders if o.side == "sell"]:
        try:
            if o.close_all:
                r = trading.close_position(o.symbol)
            else:
                r = trading.submit_order(MarketOrderRequest(
                    symbol=o.symbol, notional=o.notional, side=OrderSide.SELL,
                    time_in_force=TimeInForce.DAY,
                    client_order_id=f"{tag}-{o.symbol}-s-{uuid.uuid4().hex[:6]}"))
            sell_ids.append(r.id)
            print(f"  ✔ venta {o.symbol} enviada")
        except Exception as e:  # sigue con el resto
            print(f"  ✖ venta {o.symbol}: {e}")
    if sell_ids:
        wait_for_fills(trading, sell_ids)

    cash = float(trading.get_account().cash)
    for o in [o for o in orders if o.side == "buy"]:
        amount = round(min(o.notional, cash - 1), 2)
        if amount < o.notional - 0.01:
            print(f"  ! compra {o.symbol} reducida a ${amount:,.2f} por efectivo disponible")
        if amount < min_trade:
            print(f"  – compra {o.symbol} omitida (efectivo insuficiente)"); continue
        try:
            trading.submit_order(MarketOrderRequest(
                symbol=o.symbol, notional=amount, side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY,
                client_order_id=f"{tag}-{o.symbol}-b-{uuid.uuid4().hex[:6]}"))
            cash -= amount
            print(f"  ✔ compra {o.symbol} ${amount:,.2f} enviada")
        except Exception as e:
            print(f"  ✖ compra {o.symbol}: {e}")
    print("\nListo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
