Datos: 2006-04-26 → 2026-11-13. In-sample = hasta 2012-04-09 (periodo del libro de Chan). Costos: 5 bps por lado.

### Pruebas de cointegración

|                                  |   p-valor Engle-Granger | ¿Cointegrado (5%)?   |   Half-life (días) |
|:---------------------------------|------------------------:|:---------------------|-------------------:|
| ('EWC/EWA', 'In-sample (libro)') |                    0.07 | no                   |              28.58 |
| ('EWC/EWA', 'Out-of-sample')     |                    0.19 | no                   |              94.76 |
| ('GLD/GDX', 'In-sample (libro)') |                    0.94 | no                   |             132.64 |
| ('GLD/GDX', 'Out-of-sample')     |                    0.14 | no                   |             103.83 |
| ('XLE/XOP', 'In-sample (libro)') |                    0.2  | no                   |              41.4  |
| ('XLE/XOP', 'Out-of-sample')     |                    1    | no                   |             inf    |


### Resultados por par y método

|                                                   | CAGR   |   Sharpe | MaxDD   |   Sharpe sin costos | Exposición   |
|:--------------------------------------------------|:-------|---------:|:--------|--------------------:|:-------------|
| ('EWC/EWA', 'Kalman', 'In-sample (libro)')        | 9.0%   |     1.21 | -7.8%   |                2.01 | 29.7%        |
| ('EWC/EWA', 'Kalman', 'Out-of-sample')            | 0.4%   |     0.15 | -8.0%   |                0.8  | 8.2%         |
| ('EWC/EWA', 'Kalman 2σ', 'In-sample (libro)')     | 9.2%   |     1.73 | -5.3%   |                2.01 | 9.9%         |
| ('EWC/EWA', 'Kalman 2σ', 'Out-of-sample')         | 0.9%   |     0.53 | -2.5%   |                0.6  | 1.0%         |
| ('EWC/EWA', 'Bollinger 20d', 'In-sample (libro)') | -1.9%  |    -0.15 | -15.7%  |                0.02 | 75.5%        |
| ('EWC/EWA', 'Bollinger 20d', 'Out-of-sample')     | -2.2%  |    -0.3  | -31.7%  |               -0.03 | 77.8%        |
| ('GLD/GDX', 'Kalman', 'In-sample (libro)')        | -1.3%  |    -0.06 | -21.0%  |                0.75 | 45.8%        |
| ('GLD/GDX', 'Kalman', 'Out-of-sample')            | -5.0%  |    -0.84 | -55.7%  |                0.7  | 50.3%        |
| ('GLD/GDX', 'Kalman 2σ', 'In-sample (libro)')     | 4.0%   |     0.51 | -9.3%   |                0.86 | 21.3%        |
| ('GLD/GDX', 'Kalman 2σ', 'Out-of-sample')         | 1.3%   |     0.29 | -13.2%  |                0.98 | 25.6%        |
| ('GLD/GDX', 'Bollinger 20d', 'In-sample (libro)') | 2.6%   |     0.3  | -14.4%  |                0.47 | 76.7%        |
| ('GLD/GDX', 'Bollinger 20d', 'Out-of-sample')     | -2.3%  |    -0.3  | -32.4%  |               -0.06 | 79.8%        |
| ('XLE/XOP', 'Kalman', 'In-sample (libro)')        | -1.6%  |    -0.36 | -11.0%  |                0.37 | 14.3%        |
| ('XLE/XOP', 'Kalman', 'Out-of-sample')            | -2.4%  |    -0.4  | -30.5%  |                0.74 | 33.1%        |
| ('XLE/XOP', 'Kalman 2σ', 'In-sample (libro)')     | 1.5%   |     0.53 | -4.1%   |                0.69 | 3.6%         |
| ('XLE/XOP', 'Kalman 2σ', 'Out-of-sample')         | 0.0%   |     0.02 | -20.4%  |                0.42 | 13.3%        |
| ('XLE/XOP', 'Bollinger 20d', 'In-sample (libro)') | -1.3%  |    -0.15 | -16.3%  |                0.07 | 76.9%        |
| ('XLE/XOP', 'Bollinger 20d', 'Out-of-sample')     | -3.9%  |    -0.58 | -50.7%  |               -0.34 | 80.5%        |


### Cartera igual-ponderada de los 3 pares (Kalman)

|                   | CAGR   |   Sharpe | MaxDD   |
|:------------------|:-------|---------:|:--------|
| In-sample (libro) | 2.2%   |     0.49 | -6.6%   |
| Out-of-sample     | -2.3%  |    -0.77 | -29.3%  |


### Retornos anuales (Kalman)

|      | EWC/EWA Kalman   | GLD/GDX Kalman   | XLE/XOP Kalman   | Cartera 3 pares   |
|-----:|:-----------------|:-----------------|:-----------------|:------------------|
| 2006 | 3.2%             | 1.6%             | -0.7%            | 1.4%              |
| 2007 | 1.0%             | -8.2%            | 0.4%             | -2.3%             |
| 2008 | 53.3%            | -1.9%            | -3.2%            | 14.3%             |
| 2009 | 3.9%             | 0.6%             | -1.1%            | 1.2%              |
| 2010 | -1.1%            | 1.2%             | -2.4%            | -0.7%             |
| 2011 | 1.6%             | 2.6%             | -3.5%            | 0.3%              |
| 2012 | -1.1%            | -8.4%            | 0.4%             | -3.1%             |
| 2013 | -1.5%            | 6.5%             | -1.6%            | 1.1%              |
| 2014 | 1.9%             | 1.2%             | -0.3%            | 1.0%              |
| 2015 | 0.8%             | -9.3%            | -1.7%            | -3.4%             |
| 2016 | -4.3%            | -4.2%            | -5.7%            | -4.7%             |
| 2017 | 0.3%             | -10.7%           | -5.0%            | -5.2%             |
| 2018 | 0.5%             | -3.9%            | -6.5%            | -3.3%             |
| 2019 | -0.1%            | -4.6%            | -1.9%            | -2.2%             |
| 2020 | 17.3%            | -1.1%            | 14.3%            | 10.4%             |
| 2021 | -1.2%            | -7.8%            | -0.7%            | -3.3%             |
| 2022 | -4.4%            | -4.3%            | -4.3%            | -4.3%             |
| 2023 | -0.9%            | -8.3%            | -5.7%            | -5.0%             |
| 2024 | 0.7%             | -2.8%            | -5.9%            | -2.7%             |
| 2025 | -1.7%            | -3.8%            | -3.9%            | -3.1%             |
| 2026 | 0.8%             | -12.4%           | -3.3%            | -5.0%             |

