# Data source guide

Source availability and terms change. Verify coverage, redistribution rights,
rate limits, adjustments, and venue rules at use time. A successful download is
not proof of research quality.

| Market | Practical starting points | Professional or deeper history | Common caveats |
|---|---|---|---|
| Crypto | CCXT exchange APIs; exchange public archives | Tardis, Kaiko, CoinAPI | Symbol changes, outages, exchange-specific volume, funding and 24/7 calendar |
| US equities | Alpaca; limited Yahoo history | Databento, Massive, exchange-licensed vendors | Intraday retention, corporate actions, delistings, consolidated versus venue feed |
| China A-shares | AkShare and available Tushare interfaces | Wind, Choice, licensed research platforms | Unstable public endpoints, adjustment conventions, halts and price limits |
| Hong Kong equities | Limited Yahoo history; Futu OpenAPI where authorized | Wind, Choice, exchange-licensed vendors | Session breaks, corporate actions, lot sizes and intraday retention |

Prefer official archives or documented APIs over scraped pages. Cache immutable
raw files, write a source manifest, and normalize into a separate processed
file. Never commit credentials or private vendor URLs. Read credentials only
from environment variables or the user's secret manager.

For order-book work, require event-level L2/L3 data. Do not reconstruct queues
or intrabar event order from OHLCV bars.
