# Bitcoin Portfolio Analytics Engine (Foundry-Integrated)

A multi-source Bitcoin portfolio tracker running in **Palantir Foundry**. Ingests transaction data from 7 sources, standardizes it through Pipeline Builder, backs an Ontology Object Type, and surfaces live portfolio metrics via Foundry Functions, a Workshop dashboard, and a Contour analytics dashboard.

**Foundry Instance:** `jaylonjones.usw-18.palantirfoundry.com`

**Foundry tools used:** Transforms (Python), Pipeline Builder, Ontology, Functions (Ontology SDK), Workshop, Contour

---

## Architecture Overview

The project spans four layers, two Foundry code repositories, and a set of no-code Pipeline Builder pipelines.

### Layer 1 — Data Ingestion

Two ingestion patterns feed raw data into Foundry:

**Automated (API):**
- `gemini_rewards_ingestion.py` in the `API_Data_Ingestion` repo pulls Gemini credit card reward transactions via the Gemini `/v1/transfers` endpoint. Uses `@incremental()` transforms so each run only processes new records. Authenticates with HMAC-SHA384 signing, secrets stored in Magritte sources. For each new reward, hits the Kraken OHLC API to capture the BTC/USD price at that exact moment. Runs on a schedule — the `Bitcoin Transaction` Object Type builds every 4 hours, which triggers the ingestion transform.

**Manual (CSV uploads):**
- All other sources are ingested as CSV uploads into Foundry datasets. Strike and Sparrow have dedicated Loader pipelines (union of multiple CSVs over time). The remaining sources are one-time CSV uploads.

### Layer 2 — Pipeline Builder (ETL)

Visual, no-code pipelines in Foundry that standardize, union, and enrich all source data:

- **Loader Pipelines:** Strike Loader and Sparrow Loader union multiple CSV uploads into master datasets.
- **Main Pipeline:** 8 source-specific transforms standardize raw columns into a unified 10-column schema, union them, then LEFT JOIN with a historical price dataset to fill missing exchange rates.
- **Output:** `Bitcoin Transactions Dataset` → `Bitcoin Transaction` Object Type in the Ontology.

See [PIPELINE_LOGIC.md](./PIPELINE_LOGIC.md) for the full pipeline flow.

### Layer 3 — Functions & Workshop

**Foundry Functions** (`portfolio_metrics.py` in the `Bitcoin-Savings-Tracker-Repository` repo) operate on `BitcoinTransaction` objects via the Ontology SDK to compute live portfolio metrics.

Transaction-level functions:
- `get_current_price()` — Live BTC/USD from Kraken Ticker API
- `get_total_return()` / `get_total_return_percentage()` — Per-transaction unrealized gain/loss

Portfolio-level aggregate functions:
- `total_btc_holdings()` — Total BTC counted as "stacked" (Sparrow + IBIT only)
- `total_portfolio_value()` — Current USD value of all stacked BTC (holdings * live price)
- `total_cost_basis()` — Total USD spent on all Buy transactions across every source
- `average_purchase_price()` — Weighted average USD price paid per BTC (DCA entry point)
- `total_fees_paid()` — Total fees paid in USD across all transactions
- `overall_return_percentage()` — Portfolio-level return: (portfolio value - cost basis) / cost basis
- `total_usd_profit()` — Aggregated unrealized profit across all 5 tracked sources
- Per-source profit: `total_profit_coinbase`, `total_profit_gemini`, `total_profit_exodus`, `total_profit_ibit`, `total_profit_strike`

**Workshop Dashboard** provides a transaction-level view with live KPI cards:
- **KPI card row:** BTC Price, BTC Holdings, Portfolio Value, Total Profit, Overall Return (%), Avg. Purchase Price — all powered by Foundry Functions with live Kraken API data
- **Filter sidebar:** Source, Type, ID, Datetime range
- **Transaction table:** All transaction fields + computed Total Return ($) and Return (%) columns
- **Detail panel:** Click any transaction to see all Object properties

### Layer 4 — Contour Analytics Dashboard

**BTC Savings Tracker Dashboard** built in Foundry Contour provides historical analytics across three tabs:

**Portfolio Performance tab:**
- Portfolio Value vs. Cost Basis — dual-axis line chart showing portfolio value (green) against cumulative USD spent (blue) over time
- Profit Over Time — monthly profit/loss trend line
- Percent Return Over Time — monthly return percentage trend line

**Accumulation tab:**
- Cumulative BTC Holdings — step chart showing BTC stack growing over time with each purchase
- Cumulative USD Spent — step chart showing total capital deployed over time

**DCA History tab:**
- Monthly DCA tracker table — columns: year_month, mean exchange rate, sum BTC bought, sum USD spent
- Grand total row with lifetime aggregates

**Summary Table:**
- Single-row aggregate view: total USD spent, total BTC bought, average purchase price, total fees, transaction count

---

## Source Breakdown

### Strike (Active — Primary)
- **What it is:** Main BTC purchasing platform. Also receives direct deposits as Bitcoin.
- **Ingestion:** Monthly manual CSV uploads. No GET transaction history API available from Strike. The Strike Loader pipeline unions each month's CSV into the `Strike Master Dataset`.
- **Profit tracked:** Yes — `total_profit_strike()`
- **Complexity:** Strike is used for buying BTC, receiving direct deposits (classified as "Purchase" in raw data, transformed to "Buy"), paying bills, and sending BTC to cold storage or other wallets. The `notes` field distinguishes "Send to Cold Storage" transfers from actual outflows. Sends to cold storage are excluded from profit/loss calculations since they're internal portfolio movement, not spending.

### Gemini (Active — Credit Card Rewards)
- **What it is:** Gemini credit card that auto-purchases small amounts of BTC with every credit card transaction.
- **Ingestion:** Two streams:
  - **Automated:** `gemini_rewards_ingestion.py` pulls reward transactions from the Gemini API. The `Automated_Gemini_Transformations` step renames the "Reward" type to "Buy" during standardization.
  - **Static CSV:** `031626_Gemini_BTCTra...` contains historical Gemini transactions from before the API automation was set up.
- **Profit tracked:** Yes — `total_profit_gemini()`

### Sparrow (Active — Cold Storage)
- **What it is:** Cold storage wallet. Receive-only — BTC sent here is considered long-term savings ("stacked").
- **Ingestion:** Manual CSV uploads via the Sparrow Loader pipeline.
- **Profit tracked:** No. Sparrow only receives BTC; the cost basis is already accounted for at the sending exchange. Sparrow "Receive" transactions contribute to `total_btc_holdings()`.

### IBIT (Mostly Inactive)
- **What it is:** BlackRock Bitcoin ETF held in a Roth IRA through Charles Schwab. Last purchased May 2025.
- **Ingestion:** One-time CSV upload from Schwab. If stacking resumes, may connect to the Schwab API.
- **Profit tracked:** Yes — `total_profit_ibit()`
- **Note:** IBIT positions count toward `total_btc_holdings()` because they represent long-term, tax-advantaged BTC exposure.

### Coinbase (Inactive / Legacy)
- **What it is:** No longer used. Historical buy/sell/receive data only.
- **Ingestion:** One-time CSV upload.
- **Profit tracked:** Yes — `total_profit_coinbase()`

### Exodus (Inactive / Legacy)
- **What it is:** No longer used. Historical buy/sell/receive data only.
- **Ingestion:** One-time CSV upload.
- **Profit tracked:** Yes — `total_profit_exodus()`

### CashApp (Rarely Used)
- **What it is:** Used only to receive BTC from Strike and sell it for USD for person-to-person payments. Never used to buy BTC.
- **Ingestion:** One-time CSV upload.
- **Profit tracked:** No — excluded from all profit functions because no BTC is purchased here.

---

## Key Concepts

### "Stacked" BTC
Only BTC in **Sparrow** (cold storage) and **IBIT** (Roth IRA) is considered "stacked." Everything sitting on exchanges is potentially spendable. The `total_btc_holdings()` function reflects this definition.

### Strike Profit Logic
Strike transactions include buys, direct deposits, bill payments, sends to cold storage, and sends to other wallets (e.g., CashApp). The profit function:
- **Buy:** Adds unrealized gain (current value - cost basis)
- **Sell:** Subtracts unrealized gain
- **Send (not to cold storage):** Treated as a sell — subtracts from profit since BTC left the portfolio
- **Send to Cold Storage:** Excluded — internal movement, not actual spending

### Exchange Rate Backfill
A `btc_15m_data_2018_to_2026` dataset containing 15-minute OHLC candles is LEFT JOINed with the unioned transaction data. All transaction timestamps are rounded to 15-minute intervals in each source-specific transformation (before union). This fills in exchange rates for transactions that don't have one from their source.

### Scale
The dataset currently contains ~907 transactions across all sources (~642 Buy transactions contributing to cost basis). Lifetime totals: ~1.351 BTC bought, ~$124,212 USD spent, ~$1,288 in fees.

---

## Repository Structure

```
bitcoin-savings-tracker/
├── docs/
│   ├── README.md                    # This file
│   ├── PIPELINE_LOGIC.md            # Detailed pipeline flow
│   └── screenshots/                 # Workshop, Pipeline Builder, and Contour screenshots
├── API_Data_Ingestion/              # Foundry Transforms repo (Gemini API ingestion)
│   └── transforms-python/src/myproject/datasets/
│       └── gemini_rewards_ingestion.py
└── Bitcoin-Savings-Tracker-Repository/  # Foundry Functions repo (portfolio metrics)
    └── python-functions/python/python_functions/
        └── portfolio_metrics.py
```

Both repos are hosted on the Foundry instance via Stemma Git.

---

## Foundry Links

- [Bitcoin Transaction Object Type](https://jaylonjones.usw-18.palantirfoundry.com/workspace/ontology/object-type/edqd5xlc.bitcoin-transaction/overview)
- [Bitcoin Savings Tracker Pipeline](https://jaylonjones.usw-18.palantirfoundry.com/workspace/builder/ri.eddie.main.pipeline.2b9fddfb-9b8f-4df0-ab2b-d9c09ce92f26/sandbox/86d3f258-c103-4811-ae95-06295fedff14)
- [Bitcoin Savings Tracker Workshop](https://jaylonjones.usw-18.palantirfoundry.com/workspace/module/view/latest/ri.workshop.main.module.2e0814a6-b3ab-4000-8c2a-d4839feb1660)
- [Gemini API Source (Magritte)](https://jaylonjones.usw-18.palantirfoundry.com/workspace/compass/view/ri.compass.main.folder.f410e5fc-1232-4624-b547-7c3ca93df88e)
- [Kraken API Source (Magritte)](https://jaylonjones.usw-18.palantirfoundry.com/workspace/compass/view/ri.compass.main.folder.481dd0b2-3067-4ae4-ae09-5c2bbb454751)
