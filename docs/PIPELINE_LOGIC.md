# Pipeline Builder Logic

This file documents the visual Pipeline Builder pipelines in Foundry that connect raw data to the final `Bitcoin Transaction` Object Type. These pipelines are no-code and built entirely within Foundry's Pipeline Builder UI.

---

## 1. Loader Pipelines

Loader pipelines exist for sources that receive ongoing CSV uploads. They union multiple CSVs into a single master dataset.

### Strike Loader
- **Inputs:** Multiple Strike CSV uploads (e.g., `020926_Strike_Transactions_BTCTracker`, `031726_Strike_Transactions_BTCTracker`), each with 11 columns
- **Flow:** CSVs → Union (11 columns) → `Strike Master Dataset`
- **Usage:** A new CSV is added at the end of each month since Strike has no API for transaction history retrieval

### Sparrow Loader
- **Inputs:** Multiple Sparrow CSV uploads (e.g., `G2025_Sparrow_Transactions`, `G31726_Sparrow_Transactions`), each with 8 columns
- **Flow:** CSVs → Union → Transform path → `Sparrow Master Dataset`
- **Usage:** A new CSV is added whenever a cold storage receive occurs

---

## 2. Main Bitcoin Savings Tracker Pipeline

The central pipeline that standardizes all sources, unions them, enriches with price data, and outputs the final dataset.

### Stage 1: Source-Specific Transformations

Each source feeds into its own transformation node that standardizes raw columns into the unified 10-column schema:

| Input Dataset | Transform Node | Source Columns | Notes |
|---------------|---------------|----------------|-------|
| `Strike Master Dataset` (11 cols) | `Strike_Transformations` (10 cols) | Raw Strike CSV columns | Transforms raw "Purchase" type to "Buy", categorizes sends/receives |
| `031926_Coinbase_Trans...` (11 cols) | `Coinbase_Transformations` (10 cols) | One-time CSV | Legacy data |
| `031626_CashApp_Trans...` (9 cols) | `Cash_App_Transformations` (10 cols) | One-time CSV | Rarely used |
| `Sparrow Master Dataset` (8 cols) | `Sparrow_Transformations` (10 cols) | From Sparrow Loader | Cold storage receives |
| `70926_Exodus_Transacti...` (10 cols) | `Exodus_Transformations` (10 cols) | One-time CSV | Legacy data |
| `031626_Gemini_BTCTra...` (10 cols) | `Gemini_Transformations` (10 cols) | Historical static CSV | Pre-API Gemini data |
| `021326_IBIT_Transactio...` (9 cols) | `IBIT_Transformations` (10 cols) | One-time CSV from Schwab | Roth IRA positions |
| `Gemini_Rewards_Autom...` (8 cols) | `Automated_Gemini_Transformations` (10 cols) | From `gemini_rewards_ingestion.py` | Renames "Reward" type to "Buy" |

### Unified Schema (10 columns)

All source-specific transforms output this standardized schema:

| Column | Description |
|--------|-------------|
| `timestamp` | Transaction datetime |
| `source` | Exchange/wallet name (Strike, Gemini, Coinbase, Exodus, IBIT, CashApp, Sparrow) |
| `type` | Standardized to: Buy, Sell, Send, Receive |
| `amount_btc` | BTC amount of the transaction |
| `amount_usd` | USD amount of the transaction |
| `exchange_rate` | BTC/USD price at time of transaction (may be null before join) |
| `fee_btc` | Transaction fee in BTC |
| `fee_usd` | Transaction fee in USD |
| `notes` | Free-text notes (e.g., "Send to Cold Storage", "Deposit (Gemini Credit Card...)") |
| `id` | Unique transaction identifier |

### Timestamp Rounding

Each source-specific transformation rounds the transaction timestamp to the nearest 15-minute interval. This is done before the union so that all rows have a rounded timestamp ready for the LEFT JOIN with `btc_15m_data_2018_to_2026` in Stage 3.

### Type Standardization Rules

The transformations normalize source-specific transaction types into four standard types:
- **Buy** — Includes direct purchases and Strike direct deposits (raw type: "Purchase") and Gemini credit card rewards (raw type: "Reward")
- **Sell** — BTC sold for USD
- **Send** — BTC sent to another wallet or address
- **Receive** — BTC received from another wallet or source

### Stage 2: Union

All 8 transformed streams feed into a single **Union** node, producing a unified dataset with 10 columns containing every transaction across all sources.

### Stage 3: Exchange Rate Enrichment (LEFT JOIN)

- **Left dataset:** The unioned transaction data
- **Right dataset:** `btc_15m_data_2018_to_2026` (12 columns) — a static CSV of 15-minute OHLC BTC/USD candle data
- **Join type:** LEFT JOIN — every transaction keeps its row regardless of match
- **Join key:** Rounded timestamp (all transaction timestamps are rounded to 15-minute intervals)
- **Purpose:** Fills in `exchange_rate` for transactions where the source data didn't provide one. Transactions that already have an exchange rate from their source (e.g., Gemini API rewards enriched via Kraken OHLC) retain their original value.

### Stage 4: Output

- `Joined_Transformations` → `Bitcoin Transactions Dataset` (deployed and built)
- `Bitcoin Transactions Dataset` backs the `Bitcoin Transaction` Object Type in the Foundry Ontology (~907 transactions)
- The Object Type has a `Rounded Timestamp` property derived from the 15-minute rounding applied in each source-specific transformation (Stage 1)
- The Object Type builds every 4 hours on a schedule, which also triggers the Gemini API ingestion transform

### Downstream Consumers

The `Bitcoin Transactions Dataset` and `Bitcoin Transaction` Object Type feed two presentation layers:

- **Workshop** — Transaction-level table with live KPI cards powered by Foundry Functions (Ontology SDK + Kraken API)
- **Contour** — SQL-driven analytics dashboard with time-series charts (Portfolio Performance, Accumulation, DCA History) querying the `Bitcoin Transactions Dataset` directly

---

## 3. Data Flow Summary

```
Strike CSVs ──► Strike Loader ──► Strike Master Dataset ──► Strike_Transformations ──┐
Coinbase CSV ──────────────────────────────────────────► Coinbase_Transformations ──┤
CashApp CSV ───────────────────────────────────────────► Cash_App_Transformations ──┤
Sparrow CSVs ─► Sparrow Loader ► Sparrow Master Dataset ► Sparrow_Transformations ──┤
Exodus CSV ────────────────────────────────────────────► Exodus_Transformations ────┼──► Union ──┐
Gemini Static CSV ─────────────────────────────────────► Gemini_Transformations ────┤          │
IBIT CSV ──────────────────────────────────────────────► IBIT_Transformations ──────┤          │
Gemini API ──► gemini_rewards_ingestion.py ────────────► Automated_Gemini_Tra... ───┘          │
                                                                                              │
btc_15m_data_2018_to_2026 ─────────────────────────────────────────────────────────────────────┼──► LEFT JOIN
                                                                                              │
                                                                     Union output (10 cols) ──┘
                                                                                                      │
                                                                                                      ▼
                                                                               Joined_Transformations
                                                                                                      │
                                                                                                      ▼
                                                                            Bitcoin Transactions Dataset
                                                                                                      │
                                                                                                      ▼
                                                                        Bitcoin Transaction (Object Type)
                                                                                      │
                                                                          ┌─────────────┴─────────────┐
                                                                          ▼                           ▼
                                                                  Workshop (Live KPIs       Contour (Historical
                                                                  + Transaction Table)      Analytics Dashboard)
```
