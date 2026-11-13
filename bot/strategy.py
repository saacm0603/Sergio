"""Señal de la Estrategia 1 (momentum de series de tiempo en ETFs).

Es exactamente la regla validada en backtests/momentum_etf.py ("TSMOM 12m (base)"):
  * peso base de cada ETF ∝ 1 / volatilidad diaria de 60 días;
  * si el retorno de 12 meses del ETF es <= 0, su peso va a SHY ("efectivo").
Función pura: no depende de Alpaca, se puede testear con cualquier serie de precios.
"""
from __future__ import annotations

import pandas as pd

UNIVERSE = ["SPY", "QQQ", "IWM", "EFA", "EEM", "TLT", "IEF", "GLD", "DBC", "VNQ"]
CASH = "SHY"
LOOKBACK_MONTHS = 12
VOL_WINDOW = 60


def target_weights(closes: pd.DataFrame, asof: pd.Timestamp | None = None) -> pd.Series:
    """closes: precios de cierre ajustados (columnas = tickers, índice = fechas).
    Devuelve pesos objetivo (suman 1) para UNIVERSE + CASH usando datos hasta `asof`."""
    missing = [s for s in UNIVERSE if s not in closes.columns]
    if missing:
        raise ValueError(f"Faltan precios de: {missing}")
    px = closes[UNIVERSE].dropna()
    if asof is None:
        asof = px.index[-1]
    px = px.loc[:asof]
    d = px.index[-1]

    past = px.index[px.index <= d - pd.DateOffset(months=LOOKBACK_MONTHS)]
    if len(past) == 0:
        raise ValueError(f"Se necesitan al menos {LOOKBACK_MONTHS} meses de historia")
    mom = px.loc[d] / px.loc[past[-1]] - 1

    vol = px.pct_change().iloc[-VOL_WINDOW:].std()
    if vol.isna().any() or (vol <= 0).any():
        raise ValueError("Volatilidad inválida; revisa los datos")
    base = (1 / vol) / (1 / vol).sum()

    w = base.where(mom > 0, 0.0)
    w[CASH] = 1 - w.sum()
    return w


def momentum_table(closes: pd.DataFrame) -> pd.DataFrame:
    """Tabla informativa (retorno 12m, volatilidad anualizada, peso) para el log."""
    px = closes[UNIVERSE].dropna()
    d = px.index[-1]
    past = px.index[px.index <= d - pd.DateOffset(months=LOOKBACK_MONTHS)][-1]
    w = target_weights(closes)
    return pd.DataFrame({
        "ret_12m": px.loc[d] / px.loc[past] - 1,
        "vol_anual": px.pct_change().iloc[-VOL_WINDOW:].std() * (252 ** 0.5),
        "peso": w.reindex(UNIVERSE),
    })
