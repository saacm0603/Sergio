"""Estrategia 3: trading de pares / cointegración en ETFs (Chan, caps. 2-3).

Dos implementaciones, ambas tal como las describe Chan:
  * Kalman (Ejemplo 3.3): hedge ratio + intercepto estimados con filtro de Kalman
    (delta=1e-4, Ve=1e-3). Largo el spread si e < -sqrt(Q), corto si e > sqrt(Q).
  * Bollinger (Ejemplo 3.2): hedge ratio por OLS móvil; z-score del spread con la misma
    ventana; entrada |z| > 1, salida al cruzar 0.

Unidad de posición: 1 acción de Y contra beta acciones de X. Retorno = P&L / exposición bruta
(sin apalancamiento). Costos: COST_BPS por lado sobre el valor negociado (incluye los
rebalanceos diarios del hedge ratio). No se modela el costo de préstamo de los cortos.

In-sample = periodo usado por Chan en el libro (hasta abr-2012). Todo lo posterior es
out-of-sample real: el libro se publicó en 2013.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import coint

sys.path.insert(0, str(Path(__file__).parent))
from common import fmt_table, load_prices, metrics  # noqa: E402

PAIRS = [("EWA", "EWC"), ("GDX", "GLD"), ("XOP", "XLE")]  # (X, Y)
START, IS_END = "2006-04-26", "2012-04-09"
COST_BPS = 5
OUT = Path(__file__).parent / "results"


def kalman_signals(x: pd.Series, y: pd.Series, delta=1e-4, ve=1e-3, k=1.0):
    """Ve está calibrado por Chan para precios de ~$20-30 (EWA/EWC). Como el filtro depende
    de la escala, ambos precios se reescalan por una constante fija (precio inicial -> 25):
    no hay look-ahead. El hedge ratio se devuelve en la escala original."""
    sx, sy = 25.0 / x.iloc[0], 25.0 / y.iloc[0]
    n = len(x)
    X = np.column_stack([x.values * sx, np.ones(n)])
    Y = y.values * sy
    vw = delta / (1 - delta) * np.eye(2)
    beta = np.zeros((n, 2))
    P = np.zeros((2, 2))
    e = np.full(n, np.nan)
    Q = np.full(n, np.nan)
    b = np.zeros(2)
    for t in range(n):
        R = P + vw if t > 0 else np.zeros((2, 2))
        xt = X[t]
        Q[t] = xt @ R @ xt + ve
        e[t] = Y[t] - xt @ b
        K = R @ xt / Q[t]
        b = b + K * e[t]
        P = R - np.outer(K, xt) @ R
        beta[t] = b
    sq = k * np.sqrt(Q)
    if k == 1.0:  # regla exacta de Chan: en posición mientras |e| > sqrt(Q)
        units = np.where(e < -sq, 1.0, np.where(e > sq, -1.0, 0.0))
    else:         # entrada a k·sqrt(Q), salida cuando e cruza 0
        units, cur = np.zeros(n), 0.0
        for t in range(n):
            if cur == 0:
                cur = 1.0 if e[t] < -sq[t] else (-1.0 if e[t] > sq[t] else 0.0)
            elif (cur == 1 and e[t] >= 0) or (cur == -1 and e[t] <= 0):
                cur = 0.0
            units[t] = cur
    units[:30] = 0.0  # período de calentamiento del filtro
    # acciones de Y por unidad = sy; hedge en acciones de X = beta * sx / sy por acción de Y
    return pd.Series(units, index=x.index), pd.Series(beta[:, 0] * sx / sy, index=x.index)


def bollinger_signals(x: pd.Series, y: pd.Series, lookback=20, entry=1.0, exit_=0.0):
    hr = pd.Series(np.nan, index=x.index)
    xv, yv = x.values, y.values
    for t in range(lookback - 1, len(x)):
        A = np.column_stack([xv[t - lookback + 1:t + 1], np.ones(lookback)])
        hr.iloc[t] = np.linalg.lstsq(A, yv[t - lookback + 1:t + 1], rcond=None)[0][0]
    spread = y - hr * x
    z = (spread - spread.rolling(lookback).mean()) / spread.rolling(lookback).std()
    pos, cur = [], 0.0
    for v in z.values:
        if np.isnan(v):
            cur = 0.0
        elif cur == 0:
            cur = 1.0 if v < -entry else (-1.0 if v > entry else 0.0)
        elif cur == 1 and v >= -exit_:
            cur = 0.0
        elif cur == -1 and v <= exit_:
            cur = 0.0
        pos.append(cur)
    return pd.Series(pos, index=x.index), hr


def pnl(x: pd.Series, y: pd.Series, units: pd.Series, hr: pd.Series, cost_bps=COST_BPS):
    sh = pd.DataFrame({"x": -units * hr, "y": units})          # acciones por unidad de spread
    px = pd.DataFrame({"x": x, "y": y})
    dollars = sh * px
    gross = dollars.abs().sum(axis=1)
    rets = px.pct_change()
    day_pnl = (dollars.shift(1) * rets).sum(axis=1)
    traded = ((sh - sh.shift(1)).abs() * px).sum(axis=1)
    denom = gross.shift(1).where(gross.shift(1) > 0, gross)
    cost = (traded * cost_bps / 1e4) / denom
    ret = (day_pnl / gross.shift(1)).replace([np.inf, -np.inf], np.nan).fillna(0) \
        - cost.replace([np.inf, -np.inf], np.nan).fillna(0)
    return ret


def half_life(spread: pd.Series) -> float:
    s = spread.dropna()
    lam = sm.OLS(s.diff().dropna(), sm.add_constant(s.shift(1).dropna())).fit().params.iloc[1]
    return -np.log(2) / lam if lam < 0 else np.inf


def main():
    OUT.mkdir(exist_ok=True)
    syms = sorted({s for p in PAIRS for s in p})
    px = load_prices(syms).loc[START:]

    rows, coint_rows, curves = [], [], {}
    for xs, ys in PAIRS:
        d = px[[xs, ys]].dropna()
        x, y = d[xs], d[ys]
        name = f"{ys}/{xs}"

        for pname, (a, b) in {"In-sample (libro)": (START, IS_END),
                              "Out-of-sample": ("2012-04-10", "2100")}.items():
            xx, yy = x.loc[a:b], y.loc[a:b]
            pval = coint(yy, xx)[1]
            beta = sm.OLS(yy, sm.add_constant(xx)).fit().params.iloc[1]
            coint_rows.append({"Par": name, "Periodo": pname, "p-valor Engle-Granger": pval,
                               "¿Cointegrado (5%)?": "sí" if pval < 0.05 else "no",
                               "Half-life (días)": half_life(yy - beta * xx)})

        variants = {"Kalman": kalman_signals(x, y),
                    "Kalman 2σ": kalman_signals(x, y, k=2.0),
                    "Bollinger 20d": bollinger_signals(x, y)}
        for vname, (units, hr) in variants.items():
            r = pnl(x, y, units, hr)
            r0 = pnl(x, y, units, hr, cost_bps=0)
            curves[f"{name} {vname}"] = r
            for pname, (a, b) in {"In-sample (libro)": (START, IS_END),
                                  "Out-of-sample": ("2012-04-10", "2100")}.items():
                m = metrics(r.loc[a:b])
                m0 = metrics(r0.loc[a:b])
                rows.append({"Par": name, "Método": vname, "Periodo": pname,
                             "CAGR": m["CAGR"], "Sharpe": m["Sharpe"], "MaxDD": m["MaxDD"],
                             "Sharpe sin costos": m0["Sharpe"],
                             "Exposición": (units.loc[a:b] != 0).mean()})

    res = pd.DataFrame(rows).set_index(["Par", "Método", "Periodo"])
    cdf = pd.DataFrame(coint_rows).set_index(["Par", "Periodo"])

    # Cartera igual-ponderada de los 3 pares con Kalman, y por año
    port = pd.DataFrame({k: v for k, v in curves.items() if k.endswith("Kalman")}).fillna(0).mean(axis=1)
    port_tbl = pd.DataFrame({
        "In-sample (libro)": metrics(port.loc[START:IS_END]),
        "Out-of-sample": metrics(port.loc["2012-04-10":]),
    }).T[["CAGR", "Sharpe", "MaxDD"]]
    yearly = pd.DataFrame({k: (1 + v).groupby(v.index.year).prod() - 1
                           for k, v in curves.items() if k.endswith("Kalman")})
    yearly["Cartera 3 pares"] = (1 + port).groupby(port.index.year).prod() - 1

    fig, ax = plt.subplots(figsize=(11, 6))
    for k, v in curves.items():
        if "2σ" in k:
            continue
        ax.plot((1 + v).cumprod(), lw=1.4 if "Kalman" in k else 0.8,
                ls="-" if "Kalman" in k else "--", label=k)
    ax.axvline(pd.Timestamp(IS_END), color="k", lw=1)
    ax.text(pd.Timestamp(IS_END), ax.get_ylim()[1] * 0.95, "  fin del periodo del libro →\n  out-of-sample",
            va="top", fontsize=9)
    ax.set_yscale("log"); ax.grid(alpha=.3); ax.legend(fontsize=8)
    ax.set_title("Estrategia 3 — Pares de ETFs (neto de costos, sin apalancamiento)")
    fig.tight_layout(); fig.savefig(OUT / "pairs_trading.png", dpi=110)

    md = [f"Datos: {px.index[0].date()} → {px.index[-1].date()}. In-sample = hasta {IS_END} "
          f"(periodo del libro de Chan). Costos: {COST_BPS} bps por lado.\n",
          "### Pruebas de cointegración\n", fmt_table(cdf), "\n",
          "### Resultados por par y método\n", fmt_table(res), "\n",
          "### Cartera igual-ponderada de los 3 pares (Kalman)\n", fmt_table(port_tbl), "\n",
          "### Retornos anuales (Kalman)\n", yearly.map(lambda v: f"{v:.1%}").to_markdown(), "\n"]
    (OUT / "pairs_trading.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
