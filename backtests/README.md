# Backtests — Estrategias 1 y 3

Datos diarios ajustados (dividendos + splits) de Yahoo Finance, 2006 → nov-2026. Los historiales de
Alpaca empiezan en 2016, así que no cubren 2008; para operar en vivo, el código usa los mismos
tickers que Alpaca. Costo asumido: **5 bps por lado** (spread + slippage; Alpaca no cobra comisión).
Sin apalancamiento. No incluye impuestos ni el costo de préstamo de los cortos.

```bash
pip install pandas numpy statsmodels matplotlib tabulate
python backtests/momentum_etf.py   # Estrategia 1 → results/momentum_etf.{md,png}
python backtests/pairs_trading.py  # Estrategia 3 → results/pairs_trading.{md,png}
```

Los precios se guardan en `backtests/data/` (no versionado); se descargan solos la primera vez.

## Estrategia 1 — Momentum de series de tiempo en 10 ETFs (mar-2007 → nov-2026)

| | CAGR | Vol | Sharpe | Max DD |
|---|---|---|---|---|
| **TSMOM 12m (base)** | 5.7% | 7.1% | 0.81 | **-12.6%** |
| SMA-200 | 5.6% | 6.8% | 0.83 | -11.7% |
| Dual momentum top-3 | 3.6% | 4.0% | 0.89 | -6.9% |
| SPY buy & hold | 10.9% | 19.6% | 0.63 | -55.2% |
| 60/40 SPY/IEF | 8.2% | 11.0% | 0.77 | -32.2% |

**Conclusión: funciona, pero como protección, no como motor de rentabilidad.**
- Su ventaja está en el riesgo: drawdown máximo de -12.6% frente a -55% del SPY. En 2008 ganó +10.2% mientras el SPY perdía -36.8%.
- Rinde la mitad que el SPY. Entre 2013 y 2019 quedó claramente por detrás del 60/40 (Sharpe 0.84 contra 1.34): en mercados alcistas tranquilos, el filtro de tendencia y el peso en bonos penalizan.
- Las variantes (3, 6 y 12 meses, SMA-200) dan resultados muy parecidos (Sharpe entre 0.74 y 0.83). Eso es buena señal: el resultado no depende de haber afinado un parámetro.
- Los costos casi no afectan (el Sharpe pasa de 0.83 a 0.81). Rebalanceo mensual: apta para cuentas pequeñas y sin problemas de PDT.
- Para igualar la volatilidad del 60/40 habría que apalancar alrededor de 1.5x. Con el interés de margen de Alpaca se pierde casi toda la ventaja.

## Estrategia 3 — Pares de ETFs (Chan): in-sample del libro frente a out-of-sample

| Par / método | Sharpe in-sample (2006-2012) | Sharpe out-of-sample (2012-2026) | Sharpe OOS sin costos |
|---|---|---|---|
| EWC/EWA Kalman (réplica de Chan) | 1.21 | 0.15 | 0.80 |
| EWC/EWA Kalman 2σ | 1.73 | 0.53 (solo 1% del tiempo invertido) | 0.60 |
| GLD/GDX Kalman | -0.06 | -0.84 | 0.70 |
| GLD/GDX Kalman 2σ | 0.51 | 0.29 | 0.98 |
| XLE/XOP Kalman | -0.36 | -0.40 | 0.74 |
| Bollinger 20d (los 3 pares) | -0.15 a 0.30 | -0.30 a -0.58 | ≤ 0 |
| **Cartera de 3 pares (Kalman)** | **0.49** | **-0.77** (CAGR -2.3%, DD -29%) | — |

**Conclusión: tal como está publicada, no conviene operarla en Alpaca.**
- **Réplica:** antes de costos, el Kalman sobre EWA/EWC da Sharpe 2.0 en el periodo del libro, cerca del 2.4 que publica Chan. La implementación es correcta.
- **Sesgo de selección:** casi toda la ganancia de EWA/EWC sale de dos episodios (fines de 2008: +53%; marzo de 2020). Fuera de esos momentos, la curva queda plana.
- **Cointegración:** ninguno de los tres pares está cointegrado al 5% en el periodo out-of-sample (Engle-Granger), y GLD/GDX tampoco lo estaba en el in-sample.
- **Costos:** antes de costos queda algo de ventaja out-of-sample (Sharpe 0.6-1.0). Pero el filtro de Kalman reajusta el hedge todos los días y entra y sale muy seguido, y 5 bps por lado bastan para borrarla. Con el umbral de 2σ se opera mucho menos y el resultado mejora, aunque sigue siendo pobre.
- Bollinger con OLS móvil de 20 días pierde en todos los pares.

## Qué haría con esto

1. **Estrategia 1:** pasarla a *paper trading* en Alpaca como núcleo defensivo de la cartera (o combinada con un 60/40).
2. **Estrategia 3:** no operarla con capital real. Si se quiere seguir investigando: elegir los pares por cointegración rodante (volver a hacer la prueba cada año), usar órdenes límite para bajar costos, rebalancear el hedge solo al entrar y aplicar el umbral de 2σ, y validar cada cambio *fuera de muestra*.

Recordatorio: un backtest no garantiza resultados futuros. Esto no es asesoría financiera.
