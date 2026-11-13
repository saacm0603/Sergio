"""Utilidades comunes: descarga de precios (Yahoo Finance, con caché) y métricas."""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
TRADING_DAYS = 252


def _download(symbol: str) -> pd.DataFrame:
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
           "?period1=0&period2=9999999999&interval=1d&events=div,split")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                payload = json.load(r)
            break
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)
    res = payload["chart"]["result"][0]
    q = res["indicators"]["quote"][0]
    df = pd.DataFrame({
        "open": q["open"], "high": q["high"], "low": q["low"],
        "close": q["close"], "volume": q["volume"],
        "adjclose": res["indicators"]["adjclose"][0]["adjclose"],
    }, index=pd.to_datetime(res["timestamp"], unit="s").normalize())
    return df.dropna(subset=["close"])


def load_prices(symbols: list[str], field: str = "adjclose", refresh: bool = False) -> pd.DataFrame:
    """Precios diarios (ajustados por dividendos y splits por defecto)."""
    DATA_DIR.mkdir(exist_ok=True)
    cols = {}
    for s in symbols:
        f = DATA_DIR / f"{s}.csv"
        if refresh or not f.exists():
            _download(s).to_csv(f)
        df = pd.read_csv(f, index_col=0, parse_dates=True)
        cols[s] = df[field]
    out = pd.DataFrame(cols)
    out = out[~out.index.duplicated(keep="last")]
    return out.sort_index()


def metrics(ret: pd.Series) -> dict:
    """Métricas estándar a partir de retornos diarios."""
    ret = ret.dropna()
    if len(ret) == 0:
        return {}
    eq = (1 + ret).cumprod()
    years = len(ret) / TRADING_DAYS
    cagr = eq.iloc[-1] ** (1 / years) - 1
    vol = ret.std() * np.sqrt(TRADING_DAYS)
    sharpe = ret.mean() / ret.std() * np.sqrt(TRADING_DAYS) if ret.std() > 0 else np.nan
    dd = eq / eq.cummax() - 1
    downside = ret[ret < 0].std() * np.sqrt(TRADING_DAYS)
    return {
        "CAGR": cagr,
        "Vol": vol,
        "Sharpe": sharpe,
        "Sortino": ret.mean() * TRADING_DAYS / downside if downside > 0 else np.nan,
        "MaxDD": dd.min(),
        "Calmar": cagr / abs(dd.min()) if dd.min() < 0 else np.nan,
    }


def metrics_table(rets: dict[str, pd.Series]) -> pd.DataFrame:
    return pd.DataFrame({k: metrics(v) for k, v in rets.items()}).T


def fmt_table(df: pd.DataFrame) -> str:
    """Tabla markdown con % para CAGR/Vol/MaxDD."""
    d = df.copy()
    for c in d.columns:
        if c in ("CAGR", "Vol", "MaxDD", "Exposición", "Turnover/año"):
            d[c] = d[c].map(lambda v: f"{v:.1%}" if pd.notna(v) else "–")
        elif d[c].dtype.kind == "f":
            d[c] = d[c].map(lambda v: f"{v:.2f}" if pd.notna(v) else "–")
    return d.to_markdown()
