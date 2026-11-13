# Bot de momentum en ETFs para Alpaca

Automatiza la **Estrategia 1** del backtest ([`backtests/README.md`](../backtests/README.md)):
el último día hábil de cada mes, unos minutos antes del cierre, rebalancea la cartera entre
10 ETFs (SPY, QQQ, IWM, EFA, EEM, TLT, IEF, GLD, DBC, VNQ) y SHY.

- Cada ETF pesa en proporción inversa a su volatilidad de 60 días.
- Si su retorno de 12 meses es ≤ 0, su parte se pasa a SHY (bonos del Tesoro a 1-3 años).
- Órdenes a mercado en dólares (acciones fraccionarias). Primero vende y luego compra.
- **No toca** otras posiciones que tengas en la cuenta.
- Opera **una sola vez por mes**: si ya hay órdenes `tsmom-AAAAMM`, no hace nada.
- **Paper trading por defecto.** Para dinero real hay que poner `ALPACA_PAPER=false` a propósito.

## 1. Obtén tus claves de la cuenta paper

En https://app.alpaca.markets, cambia a la cuenta **Paper** y genera tus claves en *API Keys*.
**Nunca** las subas al repositorio ni las pegues en un chat.

## 2. Pruébalo en tu computadora (simulación, no envía nada)

```bash
pip install -r bot/requirements.txt
```

```bash
export ALPACA_API_KEY="tu_key" ALPACA_SECRET_KEY="tu_secret"
```

```bash
python bot/momentum_bot.py --force
```

Muestra la señal (retorno a 12 meses, volatilidad y peso de cada ETF) y las órdenes que
enviaría. Para enviarlas de verdad a la cuenta paper hoy mismo:

```bash
python bot/momentum_bot.py --force --execute
```

## 3. Automatízalo con GitHub Actions (gratis)

1. En GitHub: *Settings → Secrets and variables → Actions → New repository secret*:
   - `ALPACA_API_KEY`
   - `ALPACA_SECRET_KEY`
2. (Opcional) en la pestaña *Variables*:
   - `BOT_CAPITAL`: dólares que gestiona el bot (por ejemplo `5000`). Por defecto usa todo el equity, menos tus otras posiciones.
   - `ALPACA_PAPER`: déjalo sin definir (= paper). Ponlo en `false` **solo** cuando quieras operar con dinero real.
3. Haz merge de esta rama en la rama principal: GitHub solo ejecuta los workflows programados desde la rama por defecto.
4. Pruébalo a mano: *Actions → "Bot momentum ETFs (Alpaca)" → Run workflow*, con `force` marcado y `execute` sin marcar.

El workflow corre dos veces por día hábil. Casi todos los días termina en segundos con
"hoy no es el último día hábil del mes". Puedes revisar cada ejecución en la pestaña *Actions*.

## Diferencias con el backtest

- **Momento de la ejecución:** el backtest ejecuta al cierre del día *siguiente* a la señal. El bot calcula la señal con el precio de minutos antes del cierre y ejecuta ese mismo día. El efecto es pequeño.
- **Datos:** el bot usa el feed gratuito IEX de Alpaca. Los precios de cierre pueden diferir un poco del consolidado (SIP). Con Algo Trader Plus, pon `ALPACA_DATA_FEED=sip`.
- **Efectivo:** deja un 1% sin invertir para cubrir redondeos.

## Tests

```bash
pip install pytest && python -m pytest tests
```

Incluyen una comprobación de que la señal del bot es **idéntica** a la del backtest en los
últimos 36 rebalanceos.

> Esto no es asesoría financiera. Corre el bot en paper durante varios meses antes de
> considerar dinero real, y nunca inviertas lo que no puedas permitirte perder.
