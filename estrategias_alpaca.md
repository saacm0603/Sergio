# Estrategias de trading algorítmico para Alpaca

Investigación basada en:

1. **Ernest P. Chan — *Algorithmic Trading: Winning Strategies and Their Rationale* (Wiley, 2013)** — PDF en `israeldi/Final-Project-EECS545`.
2. **QuantConnect LEAN** — motor open-source (Python/C#) para backtesting y trading en vivo; **soporta Alpaca** como broker y como proveedor de datos (`lean live`, cloud o local).
3. **nickmccullum/algorithmic-trading-python** — tres proyectos didácticos: S&P 500 equal-weight, momentum cuantitativo y value cuantitativo.
4. Documentación oficial de Alpaca (órdenes, datos de mercado, reglas de margen).

> ⚠️ Las cifras de APR/Sharpe citadas son **backtests del libro de Chan (periodos 2004–2012)**, sin costos completos en muchos casos. El propio Chan advierte que varias se degradaron después de publicarse. Nada de esto es asesoría financiera: toda estrategia debe re-validarse con datos recientes y correrse primero en la cuenta *paper* de Alpaca.

---

## 1. Qué permite (y qué no) Alpaca — restricciones que filtran las estrategias

| Capacidad | Implicación para estrategias |
|---|---|
| Acciones y ETFs de EE. UU., comisión $0 | Ideal para estrategias en acciones/ETFs. El costo real es *spread* + slippage. |
| `time_in_force` = `opg` / `cls` (órdenes al open / al cierre: MOO, LOO, MOC, LOC) | Permite ejecutar exactamente en la subasta de apertura/cierre → clave para *buy-on-gap*, PEAD y estrategias de cierre. |
| Órdenes bracket, OCO, OTO, trailing stop | Stops y take-profit nativos (útil en momentum). |
| Venta en corto (cuenta margin, solo activos *easy-to-borrow*) | Pares/long-short son posibles en ETFs y large caps; difícil en small caps. |
| Acciones fraccionarias | Diversificar con poco capital (equal-weight, rankings). |
| Opciones (incl. multi-leg) | Spreads, covered calls, cash-secured puts. |
| Cripto 24/7 (solo largo) | Momentum/tendencia en BTC/ETH; no hay shorts. |
| **No** futuros ni forex | Las estrategias de Chan en futuros (roll returns, TU, FSTX) y divisas **no aplican directamente**; hay que usar ETFs proxy. |
| Datos gratis = feed **IEX** (un solo exchange); SIP consolidado requiere *Algo Trader Plus* | Para señales intradía (gaps, aperturas) usar SIP o al menos datos históricos SIP (>15 min de antigüedad son gratis). Chan insiste: backtestear con precios de la bolsa primaria vs. consolidados cambia los resultados. |
| Regla PDT ($25k / 4 day-trades en 5 días) | FINRA aprobó reemplazarla por un sistema de *intraday margin* (mínimo $2,000), con 12 meses de transición. **Verifica el estado actual en tu cuenta** antes de correr estrategias intradía con < $25k. |

---

## 2. Ranking de estrategias recomendadas para Alpaca

Criterios: robustez (lógica económica clara, pocos parámetros — principio central de Chan), aplicabilidad directa en Alpaca, capital mínimo y costos de ejecución.

| # | Estrategia | Tipo | Frecuencia | Necesita shorts | Evidencia (fuente) | Dificultad |
|---|---|---|---|---|---|---|
| 1 | Momentum de series de tiempo / trend-following en ETFs | Momentum | Diaria-mensual | No (versión long/cash) | Chan cap. 6 | Baja |
| 2 | Momentum cuantitativo cross-sectional (HQM) | Momentum | Mensual | No | McCullum §4 + literatura (Jegadeesh-Titman) | Baja |
| 3 | Pares / cointegración en ETFs (Bollinger o Kalman) | Reversión a la media | Diaria | Sí (ETFs ETB) | Chan cap. 2-3: Kalman EWA-EWC APR 26.2%, Sharpe 2.4 | Media |
| 4 | *Buy-on-Gap* (reversión intradía en acciones del S&P 500) | Reversión a la media | Intradía (open→close) | No | Chan cap. 4: APR 8.7%, Sharpe 1.5 | Media |
| 5 | Long-short lineal cross-sectional (Khandani-Lo) | Reversión a la media | Diaria | Sí | Chan cap. 4: APR 13.7%, Sharpe 1.3 (2007–2011) | Media |
| 6 | PEAD (deriva post-earnings) | Momentum por noticias | Intradía | Opcional | Chan cap. 7: APR 6.7%, Sharpe 1.5 | Media-alta (requiere calendario de earnings) |
| 7 | Rebalanceo de ETFs apalancados cerca del cierre | Momentum intradía | Intradía (15 min antes del cierre) | No | Chan cap. 7: DRN APR 15%, Sharpe 1.8 | Media |
| 8 | Value cuantitativo (multi-ratio) | Factor | Trimestral | No | McCullum §5 | Baja (necesita fundamentales externos) |
| 9 | Tendencia en cripto (BTC/ETH) | Momentum | Diaria | No | Extensión de Chan cap. 6 a cripto | Baja |

### 2.1 Momentum de series de tiempo en ETFs (recomendada para empezar)

**Racional (Chan cap. 6):** la persistencia de tendencias surge de la difusión lenta de información, del *herding* y de flujos forzados de fondos. Las reglas simples (signo del retorno de N días, precio sobre la media móvil, nuevo máximo de N días) funcionan en muchos activos, y el stop-loss **sí** es coherente con momentum (a diferencia de la reversión a la media).

**Implementación en Alpaca:**
- Universo: SPY, QQQ, IWM, EFA, EEM, TLT, IEF, GLD, DBC, VNQ.
- Señal: largo si el retorno de 12 meses (o precio > SMA-200) es positivo; si no, efectivo / BIL / SHY.
- Rebalanceo mensual con órdenes `cls` (MOC) o `day` límite.
- Sizing por volatilidad inversa (riesgo igual por activo).
- Pocas operaciones → no hay problemas de PDT, el costo de spread es bajo.

### 2.2 Momentum cuantitativo "High-Quality Momentum" (McCullum §4)

**Idea:** calcular percentiles de retorno a 1, 3, 6 y 12 meses para cada acción del S&P 500; el *HQM score* es el promedio de percentiles; comprar el top 50 con pesos iguales (fraccionarias en Alpaca).
- Mejora práctica: excluir el último mes (efecto de reversión de corto plazo) y combinar con filtro de tendencia del mercado (SPY > SMA-200) para evitar los *crashes* de momentum que Chan documenta en 2008-2009.
- **Nota:** el repo de McCullum usa la API de IEX Cloud (sandbox), que dejó de operar; sustituirla por los datos históricos de Alpaca (`get_stock_bars`).

### 2.3 Trading de pares / cointegración en ETFs (Chan caps. 2-3)

**Racional:** dos ETFs expuestos al mismo factor económico (Australia vs. Canadá: EWA/EWC; oro vs. mineras: GLD/GDX) forman un spread estacionario.
1. Verifica cointegración con CADF o Johansen y calcula la **vida media** (*half-life*) de la reversión — úsala como lookback.
2. Hedge ratio dinámico: regresión móvil o, mejor, **filtro de Kalman** (en el libro, Kalman sobre EWA-EWC: APR 26.2%, Sharpe 2.4; la cartera Johansen EWA-EWC-IGE: APR 12.6%, Sharpe 1.4).
3. Entrada a ±1–2 desviaciones estándar del z-score; salida cerca de 0. **Sin stop-loss** (contradice la tesis), pero sí stop por tiempo (≈ 2-3× half-life) y reprueba de cointegración periódica.
- En Alpaca: requiere cuenta margin; los ETFs grandes casi siempre son *easy-to-borrow*. Verifica `shortable` y `easy_to_borrow` con `get_asset`.

### 2.4 Buy-on-Gap (Chan cap. 4)

**Reglas:**
1. Universo: S&P 500.
2. Comprar acciones cuyo open esté por debajo del mínimo del día anterior en más de 1 desviación estándar de los retornos de 90 días.
3. Filtro: el open debe estar **por encima** de la media móvil de 20 días del cierre (evita "cuchillos cayendo").
4. Comprar las 10 con peor gap; cerrar todo al cierre.
- Racional: ventas forzadas/pánico en la apertura que revierten durante el día.
- En Alpaca: calcular señal con precios pre-apertura (extended hours) y enviar `limit` + `opg` antes de las 9:28 ET; salida con orden `cls` (MOC).
- Advertencia del propio Chan: capacidad pequeña y rendimientos decrecientes desde 2009; la versión short (gap up bajo la SMA-20) rinde más en backtest pero sufre de restricciones de *borrow*. No hace falta apagarla con VIX alto: Chan muestra que con VIX > 35 el APR sube a 17.2% (al contrario que en las estrategias de momentum).

### 2.5 Long-short lineal (Khandani & Lo)

**Pesos:** `w_i = -(r_i - r_mercado) / Σ|r_k - r_mercado|` — comprar lo que más cayó vs. el promedio, vender lo que más subió. Sin parámetros, dollar-neutral.
- Chan: APR 13.7%, Sharpe 1.3 en SPX 2007–2011 (30% en 2008).
- Variante intradía: usar el retorno cierre→apertura y operar open→close (más rentable, más PDT-intensiva).
- En Alpaca: rotación diaria alta → el spread se come gran parte del edge; restringir a los ~100 nombres más líquidos y a top/bottom decil.

### 2.6 PEAD — Post-Earnings Announcement Drift (Chan cap. 7)

- Si una acción reporta resultados antes de la apertura y el gap cierre→apertura es ≥ 0.5 desv. est. (90 días) → comprar; si ≤ -0.5 → vender en corto; salir al cierre (o mantener varios días, versión clásica).
- Chan: APR 6.7%, Sharpe 1.5 en S&P 500 (2011-2012), apalancable al ser intradía.
- En Alpaca: la API de noticias (`get_news`) ayuda, pero **necesitas un calendario de earnings externo** (Alpaca no lo trae).

### 2.7 ETFs apalancados al cierre (Chan cap. 7)

- Los ETFs apalancados (2x/3x) deben rebalancear al cierre en la misma dirección del movimiento del día → presión de compra/venta predecible.
- Regla: a las 15:45 ET, si el retorno desde el cierre anterior > +2% → comprar; < -2% → vender; cerrar en el cierre (MOC con `cls`; Alpaca exige enviar MOC antes de ~15:50 ET).
- Chan: DRN APR 15%, Sharpe 1.8 (2011-2012). Pocas señales al año.

### 2.8 Value cuantitativo (McCullum §5)

- Rank compuesto de P/E, P/B, P/S, EV/EBITDA y EV/GP; comprar el top 50 más barato, rebalanceo trimestral.
- Alpaca no da fundamentales → fuente externa (SEC EDGAR, FMP, etc.). Combinado con momentum (2.2) diversifica bien.

### 2.9 Cripto

- Alpaca opera cripto 24/7 solo en largo. Aplica 2.1 (tendencia: precio > SMA-50/100 o retorno 30-90 días > 0) a BTC/USD y ETH/USD, con sizing por volatilidad.
- Las comisiones de cripto son por *maker/taker* (no $0): ver la tabla de Alpaca.

---

## 3. Gestión de riesgo (Chan cap. 8) — obligatoria en todas

- **Apalancamiento de Kelly:** `f = μ / σ²` (retorno medio en exceso / varianza). Usar **half-Kelly** por la incertidumbre en los parámetros.
- **CPPI** (Constant Proportion Portfolio Insurance) para acotar el drawdown máximo.
- **Stop-loss:** sí en momentum; **no** en reversión a la media (usar stops por tiempo).
- **Indicadores adelantados de riesgo:** VIX alto apaga momentum (FSTX: Sharpe 1.4 → 0.16 cuando VIX > 35) pero no reversión.
- Evitar sobreajuste: pocas reglas lineales, test out-of-sample, test de permutación (Chan cap. 1), cuidado con *survivorship bias* (universos históricos del S&P 500) y *look-ahead bias*.

---

## 4. Arquitectura sugerida

```
Investigación/backtest  →  Paper trading (Alpaca)  →  Live (Alpaca)
  LEAN (lean backtest)        lean live / alpaca-py      mismo código
  o pandas + vectorbt
```

- **Opción A — QuantConnect LEAN:** `pip install lean`, `lean project-create`, `lean backtest`, y `lean live` eligiendo *Alpaca* como broker. Ventaja: el mismo código hace backtest y live, con modelo de fees/cuenta de Alpaca (`set_brokerage_model(BrokerageName.ALPACA, AccountType.MARGIN)`).
- **Opción B — Python directo con `alpaca-py`:** más control, menos infraestructura.

### Esqueleto mínimo (alpaca-py) — momentum de ETFs con rebalanceo mensual

```python
import os
from datetime import datetime, timedelta
import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

KEY, SECRET = os.environ["APCA_API_KEY_ID"], os.environ["APCA_API_SECRET_KEY"]
data = StockHistoricalDataClient(KEY, SECRET)
trading = TradingClient(KEY, SECRET, paper=True)  # ¡paper primero!

UNIVERSE = ["SPY", "QQQ", "IWM", "EFA", "EEM", "TLT", "IEF", "GLD", "DBC", "VNQ"]

bars = data.get_stock_bars(StockBarsRequest(
    symbol_or_symbols=UNIVERSE, timeframe=TimeFrame.Day,
    start=datetime.now() - timedelta(days=400), feed="iex",  # "sip" si tienes suscripción
)).df
close = bars["close"].unstack(level=0)

mom_12m = close.iloc[-1] / close.iloc[-252] - 1
vol = close.pct_change().iloc[-60:].std()
selected = mom_12m[mom_12m > 0].index           # solo activos en tendencia
weights = (1 / vol[selected]) / (1 / vol[selected]).sum()  # volatilidad inversa

equity = float(trading.get_account().equity)
for sym in UNIVERSE:
    target = equity * weights.get(sym, 0.0)
    try:
        current = float(trading.get_open_position(sym).market_value)
    except Exception:
        current = 0.0
    delta = round(target - current, 2)
    if abs(delta) < 50:  # evita micro-órdenes
        continue
    trading.submit_order(MarketOrderRequest(
        symbol=sym, notional=abs(delta),
        side=OrderSide.BUY if delta > 0 else OrderSide.SELL,
        time_in_force=TimeInForce.DAY,
    ))
```

### Esqueleto — señal de pares con z-score (hedge ratio por regresión móvil)

```python
import numpy as np
import statsmodels.api as sm

def pair_signal(y: pd.Series, x: pd.Series, lookback: int, entry=1.0, exit=0.0):
    """Devuelve +1 (largo spread: comprar y, vender x), -1 o 0. lookback ≈ half-life."""
    yy, xx = y.iloc[-lookback:], x.iloc[-lookback:]
    beta = sm.OLS(yy, sm.add_constant(xx)).fit().params.iloc[1]
    spread = yy - beta * xx
    z = (spread.iloc[-1] - spread.mean()) / spread.std()
    if z < -entry:  return +1, beta
    if z > entry:   return -1, beta
    if abs(z) < exit + 0.25: return 0, beta
    return None, beta  # mantener posición actual

def half_life(spread: pd.Series) -> float:
    lag = spread.shift(1).dropna()
    delta = spread.diff().dropna()
    lam = sm.OLS(delta, sm.add_constant(lag)).fit().params.iloc[1]
    return -np.log(2) / lam
```

---

## 5. Plan de acción recomendado

1. **Semana 1-2:** backtest en LEAN de 2.1 (momentum ETFs) y 2.2 (HQM) con datos 2010–hoy, costos incluidos.
2. **Semana 3-4:** backtest de pares GLD/GDX y EWA/EWC con Kalman; test de cointegración rodante.
3. **Mes 2:** las que pasen (Sharpe out-of-sample > ~0.8 tras costos) → paper trading en Alpaca al menos 2-3 meses.
4. **Mes 3+:** live con capital pequeño y half-Kelly; añadir buy-on-gap/PEAD solo si tienes datos SIP y resuelves la regla PDT/intraday margin.

## Fuentes

- Chan, E. P. (2013). *Algorithmic Trading: Winning Strategies and Their Rationale*. Wiley. — https://github.com/israeldi/Final-Project-EECS545
- QuantConnect LEAN — https://github.com/QuantConnect/Lean
- LEAN + Alpaca — https://www.quantconnect.com/docs/v2/lean-cli/live-trading/brokerages/alpaca
- McCullum, N. *Algorithmic Trading in Python* — https://github.com/nickmccullum/algorithmic-trading-python
- Alpaca: Placing Orders — https://docs.alpaca.markets/us/docs/orders-at-alpaca
- Alpaca: Market Data FAQ (IEX vs SIP) — https://docs.alpaca.markets/us/docs/market-data-faq
- Alpaca: FINRA intraday margin / fin de PDT — https://docs.alpaca.markets/us/docs/understanding-finras-new-intraday-margin-rule-and-the-end-of-pdt
