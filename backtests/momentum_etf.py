"""Estrategia 1: momentum de series de tiempo (trend-following) en ETFs.

Reglas (versión base):
  * Universo de 10 ETFs multi-activo; "efectivo" = SHY (bonos del Tesoro 1-3 años).
  * Al cierre del último día hábil de cada mes:
      - cada ETF recibe un peso proporcional a 1/volatilidad(60 días);
      - si su retorno de 12 meses es <= 0, ese peso va a SHY.
  * Las órdenes se ejecutan al cierre del día siguiente (sin look-ahead).
  * Costo: COST_BPS por cada lado sobre el turnover.
Las posiciones derivan con el mercado entre rebalanceos (simulación diaria).
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from common import fmt_table, load_prices, metrics_table  # noqa: E402

UNIVERSE = ["SPY", "QQQ", "IWM", "EFA", "EEM", "TLT", "IEF", "GLD", "DBC", "VNQ"]
CASH = "SHY"
COST_BPS = 5          # 0.05% por lado (spread + slippage en ETFs líquidos; comisión $0 en Alpaca)
START = "2007-03-01"  # DBC empieza 2006-02 → 12 meses de historia
OUT = Path(__file__).parent / "results"


def simulate(prices: pd.DataFrame, target: pd.DataFrame, cost_bps: float = COST_BPS):
    """target: pesos objetivo indexados por fecha de señal (cierre). Se ejecutan al cierre siguiente."""
    rets = prices.pct_change().fillna(0.0)
    dates = prices.index
    exec_dates = {dates[dates.get_loc(d) + 1]: d for d in target.index if dates.get_loc(d) + 1 < len(dates)}
    w = pd.Series(0.0, index=prices.columns)
    out, turnover = [], 0.0
    started = False
    for d in dates:
        # retorno del día con los pesos que se tenían al cierre anterior
        r = float((w * rets.loc[d]).sum()) if started else 0.0
        growth = w * (1 + rets.loc[d])
        if growth.sum() > 0:
            w = growth / (1 + r)
        if d in exec_dates:
            tgt = target.loc[exec_dates[d]].reindex(prices.columns).fillna(0.0)
            to = float((tgt - w).abs().sum())
            r -= to * cost_bps / 1e4
            turnover += to
            w = tgt
            started = True
        out.append(r if started else np.nan)
    ret = pd.Series(out, index=dates).dropna()
    years = len(ret) / 252
    return ret, turnover / years


def month_ends(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Último día hábil de cada mes completo (excluye el mes en curso)."""
    s = pd.Series(idx, index=idx)
    ends = pd.DatetimeIndex(s.groupby([idx.year, idx.month]).last().values)
    last = idx[-1]
    if (last + pd.offsets.BDay(1)).month == last.month:  # el mes todavía no terminó
        ends = ends[:-1]
    return ends


def tsmom_weights(px: pd.DataFrame, lookback_m: int = 12, rule: str = "mom",
                  top_n: int | None = None, vol_win: int = 60) -> pd.DataFrame:
    rebal = month_ends(px.index)
    rebal = rebal[rebal >= px.index[0] + pd.DateOffset(months=lookback_m, days=5)]
    vol = px[UNIVERSE].pct_change().rolling(vol_win).std()
    sma200 = px[UNIVERSE].rolling(200).mean()
    rows = {}
    for d in rebal:
        past = px.index[px.index <= d - pd.DateOffset(months=lookback_m)]
        mom = px.loc[d, UNIVERSE] / px.loc[past[-1], UNIVERSE] - 1
        if rule == "sma":
            on = px.loc[d, UNIVERSE] > sma200.loc[d]
        else:
            on = mom > 0
        if top_n:  # dual momentum: además tiene que estar en el top-N relativo
            on &= mom.rank(ascending=False) <= top_n
        iv = 1 / vol.loc[d]
        base = iv / iv.sum()
        w = base.where(on, 0.0)
        w[CASH] = 1 - w.sum()
        rows[d] = w
    return pd.DataFrame(rows).T


def static_weights(px: pd.DataFrame, weights: dict[str, float]) -> pd.DataFrame:
    rebal = month_ends(px.index)
    return pd.DataFrame({d: pd.Series(weights) for d in rebal}).T


def main():
    OUT.mkdir(exist_ok=True)
    px = load_prices(UNIVERSE + [CASH]).dropna()
    px_bt = px.loc[px.index >= pd.Timestamp(START) - pd.DateOffset(months=13)]

    variants = {
        "TSMOM 12m (base)": tsmom_weights(px_bt, 12),
        "TSMOM 6m": tsmom_weights(px_bt, 6),
        "TSMOM 3m": tsmom_weights(px_bt, 3),
        "SMA-200": tsmom_weights(px_bt, 12, rule="sma"),
        "Dual momentum top-3": tsmom_weights(px_bt, 12, top_n=3),
    }
    bench = {
        "SPY buy&hold": static_weights(px_bt, {"SPY": 1.0}),
        "60/40 SPY/IEF": static_weights(px_bt, {"SPY": 0.6, "IEF": 0.4}),
        "Equal-weight 10 ETFs": static_weights(px_bt, {s: 0.1 for s in UNIVERSE}),
    }

    rets, tos = {}, {}
    for name, tgt in {**variants, **bench}.items():
        r, to = simulate(px_bt, tgt)
        rets[name] = r.loc[START:]
        tos[name] = to
    common_start = max(r.index[0] for r in rets.values())
    rets = {k: v.loc[common_start:] for k, v in rets.items()}

    full = metrics_table(rets)
    full["Turnover/año"] = pd.Series(tos)
    r0, _ = simulate(px_bt, variants["TSMOM 12m (base)"], cost_bps=0)
    full.loc["TSMOM 12m sin costos"] = metrics_table({"x": r0.loc[common_start:]}).iloc[0]

    periods = {"2007-2012 (incl. crisis 2008)": ("2007", "2012"),
               "2013-2019": ("2013", "2019"),
               "2020-hoy": ("2020", "2100")}
    sub = {}
    for pname, (a, b) in periods.items():
        t = metrics_table({k: v.loc[a:b] for k, v in rets.items()
                           if k in ("TSMOM 12m (base)", "SMA-200", "Dual momentum top-3",
                                    "SPY buy&hold", "60/40 SPY/IEF")})
        sub[pname] = t[["CAGR", "Sharpe", "MaxDD"]]

    yearly = pd.DataFrame({k: (1 + v).groupby(v.index.year).prod() - 1
                           for k, v in rets.items()
                           if k in ("TSMOM 12m (base)", "SPY buy&hold", "60/40 SPY/IEF")})

    # Gráfico
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True,
                             gridspec_kw={"height_ratios": [3, 1]})
    for k in ("TSMOM 12m (base)", "Dual momentum top-3", "SPY buy&hold", "60/40 SPY/IEF"):
        eq = (1 + rets[k]).cumprod()
        axes[0].plot(eq, label=k, lw=1.4 if "TSMOM" in k else 1.0)
        axes[1].plot(eq / eq.cummax() - 1, lw=1.0)
    axes[0].set_yscale("log"); axes[0].legend(); axes[0].grid(alpha=.3)
    axes[0].set_title("Estrategia 1 — Momentum de series de tiempo en ETFs (log, neto de costos)")
    axes[1].set_title("Drawdown"); axes[1].grid(alpha=.3)
    fig.tight_layout(); fig.savefig(OUT / "momentum_etf.png", dpi=110)

    last_w = variants["TSMOM 12m (base)"].iloc[-1]
    md = [f"Periodo: {common_start.date()} → {rets['SPY buy&hold'].index[-1].date()}  ",
          f"Costos: {COST_BPS} bps por lado sobre turnover.\n",
          "### Resultados completos\n", fmt_table(full), "\n",
          "### Por sub-periodo\n"]
    for pname, t in sub.items():
        md += [f"**{pname}**\n", fmt_table(t), "\n"]
    md += ["### Retornos anuales\n", yearly.map(lambda v: f"{v:.1%}").to_markdown(), "\n",
           f"### Última señal ({variants['TSMOM 12m (base)'].index[-1].date()})\n",
           last_w[last_w > 0.001].sort_values(ascending=False).map(lambda v: f"{v:.1%}")
           .to_frame("peso").to_markdown(), "\n"]
    (OUT / "momentum_etf.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
