"""Tests del bot: la señal coincide con el backtest, el plan de órdenes es correcto y
la lógica de calendario solo opera el último día hábil del mes cerca del cierre."""
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "bot"), str(ROOT / "backtests")]

from momentum_bot import Order, plan_orders, should_trade_today  # noqa: E402
from strategy import CASH, UNIVERSE, target_weights  # noqa: E402

NY = ZoneInfo("America/New_York")
DATA = ROOT / "backtests" / "data"


@pytest.mark.skipif(not (DATA / "SPY.csv").exists(), reason="sin datos en caché (corre el backtest)")
def test_signal_matches_backtest():
    import momentum_etf as bt
    px = bt.load_prices(UNIVERSE + [CASH]).dropna()
    expected = bt.tsmom_weights(px, 12)
    for d in expected.index[-36:]:  # últimos 3 años de rebalanceos
        got = target_weights(px, asof=d)
        pd.testing.assert_series_equal(got.sort_index(), expected.loc[d].sort_index(),
                                       check_names=False, atol=1e-12)


def test_weights_sum_to_one_and_cash_absorbs_negative_momentum():
    idx = pd.bdate_range("2020-01-01", "2021-06-30")
    import numpy as np
    rng = np.random.default_rng(0)
    data = {s: 100 * np.exp(np.cumsum(rng.normal(0.0005, 0.01, len(idx)))) for s in UNIVERSE}
    data["SPY"] = np.linspace(100, 50, len(idx))  # tendencia bajista clara
    w = target_weights(pd.DataFrame(data, index=idx))
    assert w.sum() == pytest.approx(1.0)
    assert w["SPY"] == 0.0 and w[CASH] > 0


def test_plan_orders():
    w = pd.Series({**{s: 0.0 for s in UNIVERSE}, "SPY": 0.5, "TLT": 0.3, CASH: 0.2})
    pos = {"SPY": 2000.0, "GLD": 1500.0, "TLT": 2980.0}
    orders = plan_orders(10_000, pos, w, min_trade=25)
    by = {(o.symbol, o.side): o for o in orders}
    assert by[("GLD", "sell")].close_all                        # objetivo 0 → cerrar
    assert by[("SPY", "buy")].notional == pytest.approx(4950 - 2000)
    assert ("TLT", "buy") not in by and ("TLT", "sell") not in by  # 2970 vs 2980 < $25
    assert by[(CASH, "buy")].notional == pytest.approx(1980)
    assert [o.side for o in orders] == sorted([o.side for o in orders], reverse=True)  # ventas primero


class FakeTrading:
    def __init__(self, now, days, close_hour=16, is_open=True):
        self.now, self.days, self.close_hour, self.is_open = now, days, close_hour, is_open

    def get_clock(self):
        close = self.now.replace(hour=self.close_hour, minute=0, second=0)
        return SimpleNamespace(is_open=self.is_open, timestamp=self.now, next_close=close)

    def get_calendar(self, req):
        return [SimpleNamespace(date=d) for d in self.days if d >= req.start]


@pytest.mark.parametrize("now,days,expected", [
    (datetime(2026, 11, 30, 15, 40, tzinfo=NY), [date(2026, 11, 30), date(2026, 12, 1)], True),
    (datetime(2026, 11, 27, 15, 40, tzinfo=NY), [date(2026, 11, 27), date(2026, 11, 30)], False),
    (datetime(2026, 11, 30, 10, 0, tzinfo=NY), [date(2026, 11, 30), date(2026, 12, 1)], False),
    (datetime(2026, 11, 30, 15, 58, tzinfo=NY), [date(2026, 11, 30), date(2026, 12, 1)], False),
])
def test_should_trade_today(now, days, expected):
    ok, _ = should_trade_today(FakeTrading(now, days), now)
    assert ok is expected


def test_should_not_trade_when_closed():
    now = datetime(2026, 11, 30, 15, 40, tzinfo=NY)
    ok, _ = should_trade_today(FakeTrading(now, [date(2026, 11, 30)], is_open=False), now)
    assert not ok
