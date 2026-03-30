# Ontology Design — Personal Financial Analytics Engine

This document explains the ontology architecture for the Personal Financial Analytics Engine: what object types exist, why they were chosen, how they relate through link types, what actions users can perform, and what trade-offs were considered. It serves as both an implementation guide and a design rationale.

The ontology spans three financial domains — **Bitcoin (money)**, **banking (cash flow)**, and **investments (growth)** — unified under a single analytical layer that enables cross-domain insights like net worth tracking, personal inflation measurement, purchase impact analysis, and BTC-denominated cost-of-living views.

---

## Table of Contents

1. [Current State](#1-current-state)
2. [Design Principles](#2-design-principles)
3. [Object Types](#3-object-types)
   - 3.1–3.3: Bitcoin Domain
   - 3.4–3.5: Banking Domain
   - 3.6–3.7: Investment Domain
   - 3.8–3.11: Cross-Domain Analytics
4. [Properties Reference](#4-properties-reference)
5. [Link Types](#5-link-types)
6. [Action Types](#6-action-types)
7. [Functions Layer](#7-functions-layer)
8. [Trade-offs and Design Decisions](#8-trade-offs-and-design-decisions)
9. [Step-by-Step Implementation Guide](#9-step-by-step-implementation-guide)
10. [Workshop Integration](#10-workshop-integration)
11. [Future Extensions](#11-future-extensions)

---

## 1. Current State

The ontology today has a single object type:

| Resource | Details |
|----------|---------|
| **Object Type** | `BitcoinTransaction` |
| **Backing Dataset** | `Bitcoin Transactions Dataset` (~907 objects) |
| **Primary Key** | `id` (unique transaction identifier from source) |
| **Properties** | `timestamp`, `source`, `type`, `amount_btc`, `amount_usd`, `exchange_rate`, `fee_btc`, `fee_usd`, `notes`, `id`, `rounded_timestamp` |
| **Functions** | 14 Python functions via Ontology SDK (portfolio metrics, per-source profit, live price) |
| **Consumers** | Workshop (KPI cards + transaction table), Contour (historical analytics) |
| **Links** | None |
| **Actions** | None |

This is a solid foundation — a single well-modeled entity backed by a clean unified dataset. But a single-object ontology doesn't demonstrate the relational modeling, writeback workflows, or multi-type navigation that Palantir roles require. The expansion below adds two object types, typed links, and three action types to close that gap.

### Planned Expansion

The ontology will grow from a Bitcoin-only tracker into a **multi-domain personal financial analytics platform** spanning three domains and 11 object types:

| Domain | Data Sources | Object Types |
|--------|-------------|--------------|
| **Bitcoin (Money)** | Strike, Gemini, Coinbase, Exodus, CashApp, Sparrow, IBIT | `BitcoinTransaction`, `BitcoinSource`, `PortfolioSnapshot` |
| **Banking (Cash Flow)** | Peach State FCU (Checking, Savings, Credit Card), American Express HYSA | `BankAccount`, `BankTransaction` |
| **Investments (Growth)** | Charles Schwab (Roth IRA, Stock Options, Dividend, Traditional Brokerage), Coinbase (non-BTC crypto), Exodus (non-BTC crypto) | `InvestmentAccount`, `InvestmentTransaction` |
| **Cross-Domain Analytics** | Derived from all three domains | `SpendingCategory`, `NetWorthSnapshot`, `MonthlyCashFlow`, `PersonalInflationMetric` |

Transaction history spans from late 2021/early 2022 to present, providing 3-4 years of financial data across all domains.

---

## 2. Design Principles

These principles come directly from Palantir's ontology design guidance and are applied throughout this document.

### Model the real world, not the raw data

The ontology should reflect the domain — transactions, sources, portfolio state over time — not the shape of CSV files or API responses. Object types represent **entities and events** that a portfolio manager would recognize. This is domain-driven design (DDD): the ontology is the semantic layer between raw datasets and the humans making decisions.

### Primary keys must be unique, deterministic, and stable

A bad primary key causes edit loss, broken links, and reindex failures. Every object type in this design uses a key that is:
- **Unique** — no two objects share a key
- **Deterministic** — the same input always produces the same key
- **Stable** — the key does not change when the backing data refreshes

### Prefer linked objects over denormalized columns

Instead of duplicating source metadata (name, active status, first transaction date) onto every transaction row, we create a separate `BitcoinSource` object and link transactions to it. This keeps the transaction dataset clean and lets source metadata update independently without reprocessing 900+ rows.

### Actions turn dashboards into applications

Without actions, Workshop is a read-only dashboard. Adding writeback actions (flag for review, record manual transactions, update source status) transforms it into an operational tool where users make decisions and the ontology captures those decisions — the core Palantir value proposition.

### Design for extensibility

The object types, links, and actions below are designed so that adding a new financial domain requires adding new objects and links, not restructuring existing ones. Each domain (Bitcoin, banking, investments) has its own object types that feed into shared cross-domain analytics objects.

### Respect domain boundaries — Bitcoin is money, not crypto

This ontology enforces a deliberate philosophical distinction: **Bitcoin is money (savings); crypto is investing (like stocks).** This is not a technical decision — it reflects how the portfolio owner thinks about and manages these assets. The implications:

- `BitcoinTransaction` is its own object type in the **Bitcoin domain**, not a subtype of a generic "CryptoTransaction." Bitcoin transactions represent savings behavior (dollar-cost averaging, self-custody transfers, long-term accumulation).
- Non-BTC crypto (ETH, SOL, etc.) from Coinbase and Exodus goes into `InvestmentTransaction` in the **Investment domain**, alongside stock trades from Schwab. Altcoin trades are speculative investments with different intent, risk profile, and time horizon than Bitcoin accumulation.
- Coinbase and Exodus appear in **both** domains: as a `BitcoinSource` (for BTC transactions) and as an `InvestmentAccount` (for non-BTC crypto). This is correct — the same platform serves two different financial functions.
- The `NetWorthSnapshot` cross-domain object reflects this separation: it reports `bitcoin_value` as its own field, distinct from `investment_value` (which includes altcoins + stocks). Bitcoin and investments are never lumped into a single "portfolio" number.

A naive ontology would group all crypto together because the data comes from the same exchanges. But domain-driven design says: **model how the owner thinks about the domain, not how the data is stored.** The owner thinks of Bitcoin as money he's saving, not a speculative position he's trading. The ontology must respect that.

---

## 3. Object Types

### 3.1 `BitcoinTransaction` (existing)

**What it represents:** A single financial event — a buy, sell, send, or receive of Bitcoin from any source.

**Why it's an object type:** Transactions are the atomic unit of a portfolio. Every metric (holdings, cost basis, return %) is derived from aggregating transactions. They are the domain's core event entity.

**Backing dataset:** `Bitcoin Transactions Dataset` — the output of the Pipeline Builder ETL that unions 8 sources and enriches with OHLC price data.

**Status:** `active`

| Property | Type | Key | Description |
|----------|------|-----|-------------|
| `id` | String | PK | Unique transaction identifier from the source exchange |
| `timestamp` | Timestamp | — | When the transaction occurred |
| `source` | String | — | Exchange or wallet name (Strike, Gemini, Coinbase, Exodus, IBIT, CashApp, Sparrow) |
| `type` | String | — | Standardized: Buy, Sell, Send, Receive |
| `amount_btc` | Double | — | BTC amount |
| `amount_usd` | Double | — | USD amount |
| `exchange_rate` | Double | — | BTC/USD price at time of transaction |
| `fee_btc` | Double | — | Fee in BTC |
| `fee_usd` | Double | — | Fee in USD |
| `notes` | String | — | Free-text notes |
| `rounded_timestamp` | Timestamp | — | Timestamp rounded to 15-minute interval (used for OHLC join) |
| `flagged` | Boolean | — | **[NEW]** Whether this transaction is flagged for review |
| `review_notes` | String | — | **[NEW]** Reviewer notes when flagged |

**New properties rationale:** `flagged` and `review_notes` are **edit-only** properties (no backing column in the source dataset). They exist solely for writeback through the "Flag Transaction for Review" action. This keeps the source pipeline clean while enabling an operational workflow on top of it.

---

### 3.2 `BitcoinSource` (new)

**What it represents:** A distinct source of Bitcoin transactions — an exchange, wallet, or brokerage account.

**Why it's an object type (not just a string column):** The `source` field on `BitcoinTransaction` is a raw string. Promoting sources to first-class objects enables:
- Storing source-level metadata (active status, total transactions, total BTC purchased) without duplicating it on every transaction row
- Navigating from a source to all its transactions through a typed link
- Taking actions on sources (e.g., marking one inactive)
- Building a Workshop "Source Breakdown" tab with source-level KPIs

**Backing dataset:** `Bitcoin_Sources` — a small derived dataset computed from the unified transaction data. One row per distinct source.

**Status:** `experimental` → promote to `active` after validation

| Property | Type | Key | Description |
|----------|------|-----|-------------|
| `source_id` | String | PK | Lowercase source name (e.g., `"strike"`, `"gemini"`) — deterministic, unique, stable |
| `source_name` | String | Title | Display name (e.g., `"Strike"`, `"Gemini"`) |
| `source_type` | String | — | Category: `exchange`, `wallet`, `brokerage` |
| `first_transaction_date` | Date | — | Earliest transaction timestamp for this source |
| `last_transaction_date` | Date | — | Most recent transaction timestamp |
| `total_transactions` | Integer | — | Count of transactions from this source |
| `total_btc_purchased` | Double | — | Sum of `amount_btc` where `type = 'Buy'` |
| `total_usd_spent` | Double | — | Sum of `amount_usd` where `type = 'Buy'` |
| `is_active` | Boolean | — | Whether this source is currently being used for purchases |

**Primary key choice:** `source_id` (lowercased source name) rather than an auto-generated UUID. There are only 7 sources, the names are stable, and using the source name as the key makes the dataset human-readable and deterministic. A UUID would add complexity with no benefit at this scale.

**Why `source_type` matters:** Grouping sources by type (exchange vs. wallet vs. brokerage) enables Workshop filters and Contour breakdowns that distinguish between custodial exchanges (Gemini, Coinbase, Strike), self-custody wallets (Sparrow, Exodus), and brokerage positions (IBIT). This is a domain distinction that a portfolio manager would naturally make.

---

### 3.3 `PortfolioSnapshot` (new)

**What it represents:** A daily point-in-time view of the entire portfolio — total holdings, value, cost basis, and return.

**Why it's an object type:** Transaction-level data answers "what happened." Snapshot data answers "how is the portfolio doing over time." These are fundamentally different questions served by different object types:
- Workshop time-series charts need a row-per-day structure, not a row-per-transaction structure
- Aggregating 900+ transactions on every page load to compute daily metrics is wasteful when a PySpark transform can precompute them
- Portfolio-level metrics (daily return %, drawdowns, rolling averages) are derived calculations that don't belong on individual transactions

**Backing dataset:** `Daily_Portfolio_Snapshots` — a PySpark-derived dataset that computes daily aggregates using window functions over the full transaction history. One row per calendar day from the first transaction to today.

**Status:** `experimental` → promote to `active` after validation

| Property | Type | Key | Description |
|----------|------|-----|-------------|
| `snapshot_id` | String | PK | ISO date string (e.g., `"2024-03-15"`) — one snapshot per day, deterministic |
| `date` | Date | Title | The calendar date of this snapshot |
| `total_holdings_btc` | Double | — | Cumulative BTC held as of this date |
| `portfolio_value_usd` | Double | — | `total_holdings_btc × closing_price` for this date |
| `cost_basis_usd` | Double | — | Cumulative USD spent on Buy transactions through this date |
| `unrealized_pnl_usd` | Double | — | `portfolio_value_usd - cost_basis_usd` |
| `daily_return_pct` | Double | — | Day-over-day change in `portfolio_value_usd` as a percentage |
| `closing_price_usd` | Double | — | BTC/USD closing price for this date (from OHLC data) |
| `transaction_count` | Integer | — | Number of transactions that occurred on this date (0 on non-transaction days) |
| `btc_bought_today` | Double | — | BTC purchased on this specific date |
| `usd_spent_today` | Double | — | USD spent on this specific date |

**Primary key choice:** `snapshot_id` as the ISO date string. Dates are inherently unique per day, deterministic, and will never change. This makes the key human-readable and naturally sortable.

**Why `closing_price_usd` is on the snapshot, not just derived:** Having the price on the snapshot row enables Workshop charts to show BTC price vs. portfolio value on the same time axis without a separate join at query time. This is a deliberate denormalization — the price is already in the OHLC dataset, but duplicating it here eliminates a runtime lookup for the most common visualization.

---

### 3.4 `BankAccount` (new — Banking Domain)

**What it represents:** A distinct bank or credit union account — checking, savings, credit card, or high-yield savings.

**Why it's an object type:** The same design reasoning that justified `BitcoinSource` applies here. Accounts have metadata (institution, type, active status) that shouldn't be duplicated on every transaction row. First-class account objects enable account-level KPIs, navigation, and actions.

**Backing dataset:** `Bank_Accounts` — a small static or semi-derived dataset. Unlike `BitcoinSource` (which is fully derived from transaction data), bank accounts may need manual definition since account metadata isn't always present in transaction exports.

**Status:** `experimental`

| Property | Type | Key | Description |
|----------|------|-----|-------------|
| `account_id` | String | PK | Deterministic slug: `"peachstate-checking"`, `"amex-hysa"` |
| `account_name` | String | Title | Display name: `"Checking"`, `"High-Yield Savings"` |
| `institution` | String | — | `"Peach State FCU"`, `"American Express"` |
| `account_type` | String | — | `checking`, `savings`, `credit_card`, `hysa` |
| `is_active` | Boolean | — | Whether the account is currently in use |
| `opening_date` | Date | — | When the account was opened (if known) |

**Accounts in scope:**

| Account ID | Institution | Type |
|------------|------------|------|
| `peachstate-checking` | Peach State FCU | Checking |
| `peachstate-savings` | Peach State FCU | Savings |
| `peachstate-credit-card` | Peach State FCU | Credit Card |
| `amex-hysa` | American Express | HYSA |

**Primary key choice:** Human-readable slugs (`institution-type`) rather than UUIDs. There are only 4 accounts, the names are stable, and slugs make the dataset and Object Explorer immediately understandable.

---

### 3.5 `BankTransaction` (new — Banking Domain)

**What it represents:** A single financial event in a bank account — a debit, credit, payment, transfer, or fee.

**Why it's an object type:** Bank transactions are the atomic unit of cash flow. Every spending metric, income calculation, savings rate, and personal inflation measurement is derived from aggregating bank transactions. They are the core event entity of the Banking domain, just as `BitcoinTransaction` is the core event entity of the Bitcoin domain.

**Backing dataset:** `Bank_Transactions_Unified` — a PySpark transform that normalizes CSV/OFX exports from Peach State and American Express into a standardized schema. Each institution has different column names, date formats, and transaction type vocabularies that the transform must harmonize.

**Status:** `experimental`

| Property | Type | Key | Description |
|----------|------|-----|-------------|
| `transaction_id` | String | PK | Deterministic hash of `account_id + date + amount + description` to ensure uniqueness and idempotent reloads |
| `date` | Date | — | Transaction date |
| `description` | String | — | Raw merchant/description string from the bank export |
| `amount` | Double | — | Transaction amount in USD. Positive = money in (credits, deposits, refunds). Negative = money out (debits, purchases, fees) |
| `category` | String | — | Spending category (auto-classified or manually assigned): `groceries`, `dining`, `subscriptions`, `housing`, `transportation`, `income`, `transfer`, `other` |
| `account_id` | String | — | FK to `BankAccount.account_id` |
| `is_income` | Boolean | — | `true` for payroll deposits, interest credits, and other income. Derived from description pattern matching or manual override |
| `is_transfer` | Boolean | — | `true` for transfers between own accounts (Peach State → Amex HYSA, checking → savings). These should be excluded from spending and income calculations to avoid double-counting |
| `btc_equivalent` | Double | — | `abs(amount) / btc_closing_price` on the transaction date. Enriched via join to `btc_daily_prices`. Shows the BTC purchasing power cost of every purchase |
| `flagged` | Boolean | — | Edit-only. Whether this transaction is flagged for review |
| `review_notes` | String | — | Edit-only. Notes when flagged |

**Primary key choice:** A deterministic hash rather than a row number or UUID. Bank CSVs don't have unique transaction IDs. A hash of `account_id + date + amount + description` ensures the same export re-imported produces the same keys, preventing duplicates. The risk of hash collision (two transactions with identical date, amount, and description on the same account) is low but real — if it occurs, append a sequence number.

**Why `btc_equivalent` is denormalized on every row:** This is a deliberate design choice. Computing `amount / btc_price` at query time would require a join to the price dataset on every function call or Workshop render. Pre-computing it in the PySpark transform costs one join at build time and makes the BTC-denominated view instantly available in Workshop charts and Contour without runtime overhead. The trade-off is that the BTC price is fixed at the transaction date's closing price, not live — which is the correct semantic for "what was this purchase worth in BTC when I made it."

**Why `is_transfer` matters:** Inter-account transfers (moving money from checking to HYSA, or from checking to Schwab) are not spending or income. Without this flag, transfers inflate both income and expense totals. The transform should auto-detect common transfer patterns (matching amounts on the same date across accounts, descriptions containing "TRANSFER", "ACH" to own accounts) and set `is_transfer = true`. Users can override via a writeback action when auto-detection fails.

---

### 3.6 `InvestmentAccount` (new — Investment Domain)

**What it represents:** A distinct investment account — brokerage, retirement, or crypto exchange/wallet used for non-BTC assets.

**Why it's an object type:** Same rationale as `BankAccount` and `BitcoinSource`. Investment accounts have metadata (institution, tax-advantaged status, account type) that drives filtering, reporting, and navigation.

**Backing dataset:** `Investment_Accounts` — a small static dataset.

**Status:** `experimental`

| Property | Type | Key | Description |
|----------|------|-----|-------------|
| `account_id` | String | PK | Deterministic slug: `"schwab-roth-ira"`, `"coinbase-crypto"` |
| `account_name` | String | Title | Display name: `"Roth IRA"`, `"Crypto (Non-BTC)"` |
| `institution` | String | — | `"Charles Schwab"`, `"Coinbase"`, `"Exodus"` |
| `account_type` | String | — | `roth_ira`, `brokerage`, `stock_options`, `dividend`, `crypto_exchange`, `crypto_wallet` |
| `tax_advantaged` | Boolean | — | `true` for Roth IRA; `false` for traditional brokerage and crypto |
| `is_active` | Boolean | — | Whether the account is currently in use |

**Accounts in scope:**

| Account ID | Institution | Type | Tax-Advantaged |
|------------|------------|------|----------------|
| `schwab-roth-ira` | Charles Schwab | Roth IRA | Yes |
| `schwab-stock-options` | Charles Schwab | Stock Options | No |
| `schwab-dividend` | Charles Schwab | Dividend Account | No |
| `schwab-brokerage` | Charles Schwab | Traditional Brokerage | No |
| `coinbase-crypto` | Coinbase | Crypto Exchange | No |
| `exodus-crypto` | Exodus | Crypto Wallet | No |

**Why Coinbase and Exodus appear here AND in `BitcoinSource`:** Per the "Bitcoin is money, not crypto" design principle, the same platform serves two financial functions. BTC transactions on Coinbase are savings events → `BitcoinTransaction` linked to `BitcoinSource`. ETH/SOL/etc. transactions on Coinbase are investment trades → `InvestmentTransaction` linked to `InvestmentAccount`. The ontology models the financial intent, not the platform.

---

### 3.7 `InvestmentTransaction` (new — Investment Domain)

**What it represents:** A single investment event — a stock/ETF trade, crypto trade, dividend payment, contribution, or withdrawal in any investment account.

**Why it's an object type:** Investment transactions are the atomic unit of the Investment domain. They capture every buy, sell, dividend, and contribution across Schwab brokerage accounts and non-BTC crypto positions. They are structurally different from bank transactions (they have symbols, quantities, price-per-unit) and philosophically different from Bitcoin transactions (they represent speculative/growth investments, not savings).

**Backing dataset:** `Investment_Transactions_Unified` — a PySpark transform that normalizes Schwab CSV exports and crypto exchange exports into a standardized schema. Schwab exports include trade confirmations, dividend history, and account activity. Crypto exports include trade history for non-BTC assets.

**Status:** `experimental`

| Property | Type | Key | Description |
|----------|------|-----|-------------|
| `transaction_id` | String | PK | Deterministic hash of `account_id + date + symbol + action + amount` |
| `date` | Date | — | Transaction/settlement date |
| `account_id` | String | — | FK to `InvestmentAccount.account_id` |
| `symbol` | String | — | Ticker or crypto symbol: `AAPL`, `VOO`, `ETH`, `SOL`. Null for cash contributions/withdrawals |
| `asset_name` | String | — | Human-readable: `"Apple Inc."`, `"Vanguard S&P 500 ETF"`, `"Ethereum"` |
| `action` | String | — | Standardized: `buy`, `sell`, `dividend`, `interest`, `contribution`, `withdrawal`, `fee`, `split`, `reward` |
| `quantity` | Double | — | Number of shares/units. Null for cash-only events (contributions, interest) |
| `price_per_unit` | Double | — | Price per share/unit at execution. Null for cash-only events |
| `amount_usd` | Double | — | Total USD value of the transaction. Positive = money/value in, negative = money/value out |
| `fees` | Double | — | Transaction fees in USD |
| `btc_equivalent` | Double | — | `abs(amount_usd) / btc_closing_price` on the transaction date. Same enrichment pattern as `BankTransaction` |

**Why `action` uses a broader vocabulary than `BitcoinTransaction.type`:** Bitcoin transactions have four types (Buy, Sell, Send, Receive) because Bitcoin is used as money. Investment transactions have a richer set of events: dividends are passive income, contributions are cash inflows, stock splits change quantity without a trade, rewards are staking/interest. The `action` field must accommodate all of these.

**Why non-BTC crypto is here, not in a separate `CryptoTransaction` type:** The owner treats altcoin trading the same as stock trading — speculative positions with entry/exit points, measured by return on investment. The shared schema (symbol, quantity, price_per_unit, action) works for both stocks and crypto. Creating a separate `CryptoTransaction` type would duplicate the schema for no functional benefit and would complicate cross-asset investment analytics.

---

### 3.8 `SpendingCategory` (new — Cross-Domain Analytics)

**What it represents:** A monthly spending aggregate for a single category — the total amount spent on groceries, dining, subscriptions, etc. in a given month.

**Why it's an object type:** Raw bank transactions answer "what did I spend?" Category aggregates answer "where does my money go?" These are different questions requiring different granularity. Precomputing monthly category totals in PySpark enables Workshop bar charts, trend lines, and budget comparisons without aggregating thousands of transactions at render time.

**Backing dataset:** `Spending_Categories_Monthly` — a PySpark transform that groups `BankTransaction` objects by `category` and month, excluding transfers and income.

**Status:** `experimental`

| Property | Type | Key | Description |
|----------|------|-----|-------------|
| `category_month_id` | String | PK | `"{category}-{YYYY-MM}"` (e.g., `"groceries-2024-03"`) — deterministic, unique per category per month |
| `category` | String | — | Spending category name |
| `month` | Date | Title | First day of the month (e.g., `2024-03-01`) |
| `total_spent` | Double | — | Sum of `abs(amount)` for debit transactions in this category and month |
| `transaction_count` | Integer | — | Number of transactions in this category and month |
| `pct_of_total_spending` | Double | — | This category's share of total spending for the month (0-100) |
| `avg_transaction_size` | Double | — | `total_spent / transaction_count` |
| `btc_equivalent_spent` | Double | — | Sum of `btc_equivalent` for all transactions in this category and month |

---

### 3.9 `NetWorthSnapshot` (new — Cross-Domain Analytics)

**What it represents:** A daily point-in-time view of total financial position across all three domains — cash, investments, and Bitcoin.

**Why it's an object type:** This is the single most important derived object in the expanded ontology. It answers "what am I worth today, and how has that changed over time?" by aggregating across all accounts and asset classes. It's the financial equivalent of `PortfolioSnapshot` but spanning the entire financial picture, not just Bitcoin.

**Backing dataset:** `Net_Worth_Snapshots` — a PySpark transform that joins daily balances from banking, investment, and Bitcoin domains. Banking balances are reconstructed from running transaction sums. Investment values require end-of-day position data or are reconstructed from transaction history + historical prices. Bitcoin values come from the existing `PortfolioSnapshot`.

**Status:** `experimental`

| Property | Type | Key | Description |
|----------|------|-----|-------------|
| `snapshot_id` | String | PK | ISO date string (e.g., `"2024-03-15"`) — same pattern as `PortfolioSnapshot` |
| `date` | Date | Title | Calendar date |
| `cash_balance` | Double | — | Total across all bank accounts (checking + savings + HYSA). Credit card balance is a negative component |
| `investment_value` | Double | — | Total market value across all investment accounts (Schwab + non-BTC crypto) |
| `bitcoin_value` | Double | — | Total BTC holdings value — sourced from `PortfolioSnapshot.portfolio_value_usd` for the same date |
| `credit_card_balance` | Double | — | Outstanding credit card balance (stored as positive number, treated as liability) |
| `total_net_worth` | Double | — | `cash_balance + investment_value + bitcoin_value - credit_card_balance` |
| `daily_change_usd` | Double | — | `today's total_net_worth - yesterday's total_net_worth` |
| `daily_change_pct` | Double | — | Day-over-day percentage change in `total_net_worth` |
| `bitcoin_pct` | Double | — | `bitcoin_value / total_net_worth × 100` — what percentage of net worth is in Bitcoin |
| `investment_pct` | Double | — | `investment_value / total_net_worth × 100` |
| `cash_pct` | Double | — | `cash_balance / total_net_worth × 100` |

**Why allocation percentages are denormalized:** Workshop pie charts and allocation trend lines need these values directly. Computing `bitcoin_value / total_net_worth` at query time is trivial, but having them precomputed lets Workshop render allocation views without any function call overhead. It also makes Contour queries simpler.

**Relationship to `PortfolioSnapshot`:** `NetWorthSnapshot` subsumes `PortfolioSnapshot` in scope but does not replace it. `PortfolioSnapshot` contains Bitcoin-specific detail (holdings in BTC, cost basis, daily BTC return) that `NetWorthSnapshot` summarizes into a single `bitcoin_value` field. Both object types coexist — `PortfolioSnapshot` for deep Bitcoin analysis, `NetWorthSnapshot` for the whole-picture view.

---

### 3.10 `MonthlyCashFlow` (new — Cross-Domain Analytics)

**What it represents:** A monthly summary of money in vs. money out — income, expenses, savings, and investment contributions.

**Why it's an object type:** Cash flow is the foundational metric for financial health. "Am I spending more than I earn?" is a monthly question, not a daily one. Precomputing monthly aggregates enables trend analysis (is my savings rate improving?), goal tracking (am I hitting my savings target?), and scenario modeling (what happens if my income changes?).

**Backing dataset:** `Monthly_Cash_Flow` — a PySpark transform that aggregates `BankTransaction` objects by month, separating income, expenses, transfers, and investment contributions.

**Status:** `experimental`

| Property | Type | Key | Description |
|----------|------|-----|-------------|
| `cashflow_id` | String | PK | `"YYYY-MM"` (e.g., `"2024-03"`) |
| `month` | Date | Title | First day of the month |
| `total_income` | Double | — | Sum of all income transactions (`is_income = true`) — payroll, interest, refunds |
| `total_expenses` | Double | — | Sum of all expense transactions (negative amounts, excluding transfers and investment contributions) |
| `investment_contributions` | Double | — | Transfers to Schwab + non-BTC crypto purchases. Money that left the bank but went to investments, not spending |
| `bitcoin_purchases` | Double | — | USD spent on BTC buys in this month (sourced from `BitcoinTransaction` where `type = 'Buy'`) |
| `net_savings` | Double | — | `total_income - abs(total_expenses)` — money earned minus money spent (excludes investment contributions since those are savings in a different form) |
| `savings_rate_pct` | Double | — | `net_savings / total_income × 100` — the percentage of income not spent |
| `total_allocation_to_assets` | Double | — | `investment_contributions + bitcoin_purchases` — total capital deployed to investments and Bitcoin |

**Why `investment_contributions` and `bitcoin_purchases` are separate from expenses:** Money transferred to Schwab or used to buy Bitcoin isn't "spent" — it's allocated to a different asset class. If you include investment contributions in expenses, a month where you invested heavily looks like a month where you overspent. The distinction between spending (money gone) and investing (money moved) is critical for accurate financial analysis.

---

### 3.11 `PersonalInflationMetric` (new — Cross-Domain Analytics)

**What it represents:** A year-over-year spending change measurement for a specific spending category — your personal inflation rate for groceries, dining, subscriptions, etc.

**Why it's an object type:** The CPI measures inflation for a statistical average consumer. Your personal inflation rate measures price changes weighted by your actual spending. If your grocery spending rose 12% year-over-year while official food CPI says 4%, that's actionable information — it means your cost of living is inflating faster than the national average, which affects how much you need to save and earn.

**Backing dataset:** `Personal_Inflation_Metrics` — a PySpark transform that compares `SpendingCategory` aggregates across the same month in consecutive years.

**Status:** `experimental`

| Property | Type | Key | Description |
|----------|------|-----|-------------|
| `metric_id` | String | PK | `"{category}-{YYYY-MM}"` (e.g., `"groceries-2024-03"`) |
| `category` | String | — | Spending category |
| `month` | Date | Title | The month being measured |
| `avg_spend_current` | Double | — | Average monthly spending in this category for the trailing 3-month period (smooths volatility) |
| `avg_spend_prior_year` | Double | — | Same calculation for the same 3-month window one year ago |
| `yoy_change_pct` | Double | — | `(avg_spend_current - avg_spend_prior_year) / avg_spend_prior_year × 100` |
| `weight_in_budget` | Double | — | This category's share of total spending (0-1). Used to compute weighted personal CPI |
| `btc_denominated_change_pct` | Double | — | YoY change in BTC-equivalent spending. If this is negative while USD spending is positive, it means BTC appreciation is outpacing your personal inflation — your purchasing power in BTC terms is improving |

**Why 3-month trailing average, not raw monthly:** Raw monthly spending is noisy — one large purchase in a category can spike a single month's total. A 3-month trailing average smooths this volatility and gives a more meaningful trend signal. This is the same approach used in economic indicators (e.g., 3-month moving average of job gains).

**Why `btc_denominated_change_pct` matters:** This is the BTC purchasing power view. If your grocery spending went from $400/month to $450/month (+12.5% in USD) but BTC went from $30K to $100K, your grocery spending went from 0.0133 BTC to 0.0045 BTC (-66% in BTC). This metric makes the case for Bitcoin as a hedge against personal inflation tangible with your own data.

---

## 4. Properties Reference

### Naming Conventions

| Convention | Rule | Example |
|------------|------|---------|
| Object type API name | PascalCase | `BitcoinTransaction`, `BankAccount`, `NetWorthSnapshot` |
| Property API name | camelCase | `amountBtc`, `accountName`, `savingsRatePct` |
| Display name | Human-readable | "Amount (BTC)", "Account Name", "Savings Rate (%)" |
| Account/Source ID | Lowercase slug | `"peachstate-checking"`, `"schwab-roth-ira"`, `"strike"` |
| Composite PK | `"{dimension}-{YYYY-MM}"` | `"groceries-2024-03"`, `"2024-03"` |

### Property Type Selection Rationale

| Property | Type Chosen | Why Not Alternative |
|----------|-------------|-------------------|
| `amount_btc`, `amount_usd`, `amount` | Double | Float has limited action support; Double gives sufficient precision for financial amounts at this scale |
| `is_active`, `flagged`, `is_income`, `is_transfer`, `tax_advantaged` | Boolean | Simple binary state; no need for an enum status here |
| `source_type`, `account_type`, `category`, `action` | String | Could be Value Types with enum constraints in a production ontology; String is simpler and avoids Value Type management overhead |
| `date` (snapshots, transactions) | Date | Not Timestamp — daily granularity is sufficient for banking and investment transactions. Bitcoin transactions use Timestamp because OHLC join requires sub-day precision |
| `review_notes`, `description` | String | `review_notes` is edit-only (writeback); `description` is raw source data preserved as-is |
| `btc_equivalent` | Double | Precomputed in PySpark transform via join to daily BTC prices. Not a runtime calculation |
| `yoy_change_pct`, `savings_rate_pct` | Double | Percentage stored as a number (e.g., 12.5 for 12.5%), not as a decimal (0.125). Matches the convention used in `PortfolioSnapshot.daily_return_pct` |

### Render Hints to Configure

| Property | Hint | Why |
|----------|------|-----|
| `id`, `source_id`, `snapshot_id`, `account_id`, `transaction_id`, `category_month_id`, `cashflow_id`, `metric_id` | Identifier | Prevents numeric-style formatting on ID fields |
| `amount_usd`, `amount`, `portfolio_value_usd`, `cost_basis_usd`, `total_net_worth`, `total_income`, `total_expenses`, `total_spent` | Searchable + Sortable | Users filter and rank by dollar amounts |
| `notes`, `review_notes`, `description` | Not Searchable | Large free-text fields; disable to save indexing cost |
| `exchange_rate`, `closing_price_usd`, `btc_equivalent`, `price_per_unit` | Sortable | Useful for ordering but not free-text search |
| `savings_rate_pct`, `yoy_change_pct`, `daily_change_pct`, `bitcoin_pct`, `investment_pct`, `cash_pct` | Sortable | Percentage fields used for ranking and threshold filtering |

### Shared Property Candidates

Properties that appear on multiple object types should be backed by **shared properties** to prevent metadata drift. A shared property centralizes the schema definition (name, description, base type, formatting, render hints, visibility) while each object type retains its own data and local API name. Per the DRY principle: if you've defined the same property three times, refactor it into a shared definition.

| Shared Property | Base Type | Used On | Rationale |
|----------------|-----------|---------|-----------|
| `Transaction Date` | Date | `BankTransaction.date`, `InvestmentTransaction.date` | Same semantic meaning, same formatting, same render hints across both domains |
| `USD Amount` | Double | `BankTransaction.amount`, `InvestmentTransaction.amount_usd`, `BitcoinTransaction.amount_usd` | All represent USD value of a financial event. Shared property ensures consistent currency formatting |
| `BTC Equivalent` | Double | `BankTransaction.btc_equivalent`, `InvestmentTransaction.btc_equivalent`, `SpendingCategory.btc_equivalent_spent` | All computed the same way (USD / BTC daily close). Shared property locks the formatting and render hints |
| `Is Active` | Boolean | `BankAccount.is_active`, `InvestmentAccount.is_active`, `BitcoinSource.is_active` | Identical meaning across all account/source types |
| `Flagged` | Boolean | `BitcoinTransaction.flagged`, `BankTransaction.flagged` | Same operational metadata pattern. Both are edit-only properties used for the flagging workflow |
| `Review Notes` | String | `BitcoinTransaction.review_notes`, `BankTransaction.review_notes` | Same writeback-only pattern with identical render hints (Not Searchable) |
| `Institution` | String | `BankAccount.institution`, `InvestmentAccount.institution` | Same concept — the financial institution name |

**Attaching shared properties does not change local API names.** This means existing functions, Workshop configs, and OSDK integrations referencing `BankTransaction.amount` or `BitcoinTransaction.amount_usd` continue to work after attaching the shared `USD Amount` property. Only the metadata (display name, description, formatting) is centralized.

**Relationship to interfaces:** Shared properties and interfaces complement each other at different levels. When the `FinancialTransaction` interface is eventually created (Section 11.4), its required properties (`date`, `amountUsd`, `btcEquivalent`) should use shared properties. This ensures that implementing object types not only satisfy the interface contract (structure) but also present consistent metadata (formatting, render hints) across the ontology.

### Value Formatting to Configure

Value formatting transforms raw property values into human-readable displays without changing underlying data.

| Property Pattern | Format Type | Configuration | Example |
|-----------------|-------------|---------------|---------|
| All USD amounts (`amount`, `amount_usd`, `total_spent`, `total_income`, `total_expenses`, `total_net_worth`, `portfolio_value_usd`, `cost_basis_usd`) | Numeric — Currency | Prefix: `$`, decimal places: 2, compact notation for large values | `45892.50` → `$45,892.50`; `1250000` → `$1.25M` |
| All BTC amounts (`amount_btc`, `btc_equivalent`, `total_holdings_btc`) | Numeric — Decimal | Decimal places: 8 (satoshi precision), no compact notation | `0.00150000` → `0.00150000` |
| All percentages (`savings_rate_pct`, `yoy_change_pct`, `daily_change_pct`, `bitcoin_pct`, `pct_of_total_spending`) | Numeric — Suffix | Suffix: `%`, decimal places: 1 | `12.5` → `12.5%` |
| All dates (`date`, `month`) | Date/Time | Format: `MMM DD, YYYY` | `2024-03-15` → `Mar 15, 2024` |
| Timestamps (`timestamp`) | Date/Time | Format: `MMM DD, YYYY h:mm A` with timezone | `2024-03-15T14:30:00Z` → `Mar 15, 2024 2:30 PM` |

### Conditional Formatting Rules

Conditional formatting applies color-coding and visual styling based on property values — making Workshop and Object Explorer immediately scannable.

| Object Type | Property | Rule | Formatting |
|-------------|----------|------|------------|
| `BankTransaction` | `amount` | `amount > 0` | Green text (income/credit) |
| `BankTransaction` | `amount` | `amount < 0` | Red text (expense/debit) |
| `BankTransaction` | `is_transfer` | `is_transfer = true` | Gray text (de-emphasized — not income or spending) |
| `BitcoinTransaction` | `type` | `type = "Buy"` | Green text |
| `BitcoinTransaction` | `type` | `type = "Sell"` | Red text |
| `MonthlyCashFlow` | `savings_rate_pct` | `>= 20` | Green background (strong savings) |
| `MonthlyCashFlow` | `savings_rate_pct` | `10–20` | Yellow background (moderate) |
| `MonthlyCashFlow` | `savings_rate_pct` | `< 10` | Red background (below target) |
| `PersonalInflationMetric` | `yoy_change_pct` | `> 0` | Red text (costs rising) |
| `PersonalInflationMetric` | `yoy_change_pct` | `<= 0` | Green text (costs flat or declining) |
| `PersonalInflationMetric` | `btc_denominated_change_pct` | `< 0` | Green text (BTC purchasing power improving) |
| `NetWorthSnapshot` | `daily_change_usd` | `> 0` | Green text |
| `NetWorthSnapshot` | `daily_change_usd` | `< 0` | Red text |

**Conditional formatting on a different property:** Foundry allows evaluating one property to format another. Example: color the `category` text on `PersonalInflationMetric` based on whether `yoy_change_pct` exceeds the official CPI — categories inflating faster than CPI get red text, those below get green. This uses a "compare against constant" rule where the constant is the latest CPI figure.

---

## 5. Link Types

### 5.1 `BitcoinTransaction` → `BitcoinSource` (many-to-one)

| Attribute | Value |
|-----------|-------|
| **Link name** | `transactionSource` / `sourceTransactions` |
| **Cardinality** | Many-to-one (many transactions belong to one source) |
| **Backing pattern** | **Foreign key** — the `source` property on `BitcoinTransaction` maps to `source_name` on `BitcoinSource` |
| **Editable** | No (FK-based links are read-only) |
| **API names** | `BitcoinTransaction.transactionSource` → returns one `BitcoinSource`; `BitcoinSource.sourceTransactions` → returns set of `BitcoinTransaction` |

**Why foreign key, not join table:** The relationship is inherently many-to-one and immutable — a transaction comes from exactly one source, and that doesn't change. FK links are simpler, cheaper (no separate dataset), and sufficient here. A join table would add a dataset and writeback complexity for no benefit.

**Configuration in Ontology Manager:**
1. Open `BitcoinTransaction` object type
2. Add link type → select `BitcoinSource` as the target
3. Set cardinality to many-to-one
4. Map the foreign key: `BitcoinTransaction.source` → `BitcoinSource.source_name`
5. Set API names: `transactionSource` (on the transaction side), `sourceTransactions` (on the source side)

**What this enables:**
- In Object Explorer: click a transaction → see its source; click a source → see all its transactions
- In Workshop: source-level filtering that propagates to the transaction table
- In Functions: `transaction.transactionSource.get()` to access source metadata without scanning the full source dataset

---

### 5.2 `PortfolioSnapshot` → `BitcoinTransaction` (one-to-many, conceptual)

| Attribute | Value |
|-----------|-------|
| **Link name** | `snapshotTransactions` / `transactionSnapshots` |
| **Cardinality** | One-to-many (a snapshot date can have zero or many transactions) |
| **Backing pattern** | **Foreign key** — join on date: `PortfolioSnapshot.date` matches the date portion of `BitcoinTransaction.timestamp` |
| **Editable** | No |

**Why this link is optional for v1:** The snapshot-to-transaction relationship is temporal (same date), not a true foreign key in the traditional sense. It requires a derived column on `BitcoinTransaction` that extracts the date from `timestamp` to use as the FK. This adds a pipeline step. Consider whether the navigation value justifies the complexity:
- **Include it** if Workshop needs to click a snapshot date and see that day's transactions
- **Defer it** if snapshot data is consumed primarily through time-series charts (no click-through navigation needed)

**Recommendation:** Defer this link to a later iteration. The `PortfolioSnapshot` object type delivers its primary value through time-series charts in Workshop, not through object-level navigation. Add this link only when the Workshop design calls for drill-through from a chart point to the underlying transactions.

---

### 5.3 `BankTransaction` → `BankAccount` (many-to-one)

| Attribute | Value |
|-----------|-------|
| **Link name** | `transactionAccount` / `accountTransactions` |
| **Cardinality** | Many-to-one (many transactions belong to one account) |
| **Backing pattern** | **Foreign key** — `BankTransaction.account_id` maps to `BankAccount.account_id` |
| **Editable** | No |
| **API names** | `BankTransaction.transactionAccount` → returns one `BankAccount`; `BankAccount.accountTransactions` → returns set of `BankTransaction` |

**Follows the same pattern as 5.1** (`BitcoinTransaction` → `BitcoinSource`). A bank transaction belongs to exactly one account, forever. FK link is the correct choice.

**What this enables:**
- In Workshop: select a bank account → see all its transactions, spending KPIs, and category breakdown
- In Functions: `transaction.transactionAccount.get()` to access account metadata (institution, type) without scanning the account dataset
- In Object Explorer: navigate from any transaction to its account and back

---

### 5.4 `InvestmentTransaction` → `InvestmentAccount` (many-to-one)

| Attribute | Value |
|-----------|-------|
| **Link name** | `transactionAccount` / `accountTransactions` |
| **Cardinality** | Many-to-one |
| **Backing pattern** | **Foreign key** — `InvestmentTransaction.account_id` maps to `InvestmentAccount.account_id` |
| **Editable** | No |
| **API names** | `InvestmentTransaction.transactionAccount` → returns one `InvestmentAccount`; `InvestmentAccount.accountTransactions` → returns set of `InvestmentTransaction` |

**Identical pattern to 5.3.** The consistency across domains (Bitcoin, Banking, Investment all using the same FK-based many-to-one link from transaction to account/source) is intentional — it demonstrates a repeatable ontology pattern.

---

### 5.5 `BankTransaction` → `SpendingCategory` (many-to-one, deferred)

| Attribute | Value |
|-----------|-------|
| **Link name** | `transactionCategory` / `categoryTransactions` |
| **Cardinality** | Many-to-one (many transactions map to one category-month aggregate) |
| **Backing pattern** | **Foreign key** — requires a derived `category_month_id` on `BankTransaction` computed as `"{category}-{YYYY-MM}"` matching `SpendingCategory.category_month_id` |
| **Editable** | No |

**Recommendation:** Defer this link. `SpendingCategory` is a monthly aggregate — linking individual transactions to monthly buckets adds a pipeline step (computing `category_month_id` on every transaction) for navigation value that's better served by Workshop filtering. A user selecting a category in a bar chart can filter the transaction table by `category` directly without needing a typed link.

---

### 5.6 `NetWorthSnapshot` → `PortfolioSnapshot` (one-to-one)

| Attribute | Value |
|-----------|-------|
| **Link name** | `bitcoinSnapshot` / `netWorthSnapshot` |
| **Cardinality** | One-to-one (same date) |
| **Backing pattern** | **Foreign key** — `NetWorthSnapshot.snapshot_id` matches `PortfolioSnapshot.snapshot_id` (both are ISO date strings) |
| **Editable** | No |

**Why this link is valuable:** `NetWorthSnapshot` reports a single `bitcoin_value` field. Linking to `PortfolioSnapshot` enables drill-through: click on a net worth snapshot → see the full Bitcoin breakdown (holdings, cost basis, daily BTC return, closing price) for that same day. This is cross-domain navigation — from the whole-picture view into domain-specific detail.

---

## 6. Action Types

Actions are the **write** path in Foundry. Without them, Workshop is a dashboard. With them, it becomes an operational application where users make decisions and the ontology captures those decisions.

### 6.1 "Flag Transaction for Review"

| Attribute | Value |
|-----------|-------|
| **Target** | `BitcoinTransaction` (single object) |
| **Rule type** | Modify object (declarative Ontology rules) |
| **Parameters** | `transaction` (object reference, required, hidden — auto-populated from context), `flagged` (boolean, default `true`), `review_notes` (string, required) |
| **Edits** | Sets `flagged = true` and `review_notes` to the provided text on the selected transaction |
| **Writeback dataset** | Auto-created `BitcoinTransaction_Edits` writeback overlay dataset |
| **Where it appears** | Object detail panel button in Workshop; Object Explorer single-object action |

**Why this action:**
- Demonstrates the simplest action pattern (modify one property on one object)
- Introduces writeback without touching the source pipeline
- Creates a real workflow: review flagged transactions → fix data issues → unflag

**Submission criteria:** None initially. Any user with Apply permissions can flag.

**Design notes:**
- `flagged` and `review_notes` are **edit-only properties** — they have no backing column in the source dataset. The writeback overlay stores them independently. This is the correct pattern when adding operational metadata that doesn't exist in the source data.
- The writeback dataset (`BitcoinTransaction_Edits`) overlays the source — it **does not** overwrite the backing dataset. Foundry merges the overlay on read. This preserves pipeline lineage and audit history.

---

### 6.2 "Record Manual Transaction"

| Attribute | Value |
|-----------|-------|
| **Target** | Creates a new `BitcoinTransaction` |
| **Rule type** | Create object (declarative Ontology rules) |
| **Parameters** | `source` (string, dropdown from source list), `type` (string, dropdown: Buy/Sell/Send/Receive), `amount_btc` (double, required), `amount_usd` (double, required), `exchange_rate` (double, optional — derive from `amount_usd / amount_btc` if omitted), `timestamp` (timestamp, default: current time), `notes` (string, optional), `id` (string, hidden — auto-generated UUID via `generate_uuid` type class) |
| **Edits** | Creates a new `BitcoinTransaction` object with the provided property values |
| **Where it appears** | Workshop button (top-level, not on an object); Object Explorer Exploration Actions |

**Why this action:**
- Demonstrates the create-object action pattern
- Handles the real use case of recording transactions that aren't captured by automated pipelines (e.g., a peer-to-peer OTC purchase, a forgotten transfer)
- Shows understanding of the `generate_uuid` type class for automatic primary key generation

**Parameter configuration:**
- `source` dropdown: backed by an **object set** of `BitcoinSource` objects, displaying `source_name`. This makes the dropdown dynamic — if a new source is added to the ontology, it automatically appears in the form.
- `type` dropdown: static list (Buy, Sell, Send, Receive). These four types are standardized in the pipeline and should not be free-text.
- `id`: hidden parameter with `generate_uuid` type class. The user never sees or enters the primary key.
- `timestamp`: defaults to current time via `prefill_current_timestamp` type class, but user can override for backdated entries.

**Submission criteria:**
- `amount_btc > 0` — prevents accidental zero-amount transactions
- `amount_usd > 0` for Buy/Sell types — sends and receives may have $0 USD value

---

### 6.3 "Update Source Status"

| Attribute | Value |
|-----------|-------|
| **Target** | `BitcoinSource` (single object) |
| **Rule type** | Modify object (declarative Ontology rules) |
| **Parameters** | `source` (object reference, required, hidden — auto-populated), `is_active` (boolean, required) |
| **Edits** | Sets `is_active` to the provided value on the selected source |
| **Where it appears** | Object detail panel button in Workshop; Object Explorer single-object action |

**Why this action:**
- Demonstrates modify-object on a second object type (not just `BitcoinTransaction`)
- Handles the real scenario: you stop using an exchange (Coinbase, Exodus) and want to mark it inactive so Workshop filters can separate active vs. archived sources
- The simplest possible action — one boolean toggle on one object

**UX configuration:**
- Button label: "Mark Active" or "Mark Inactive" (conditional based on current `is_active` value — configurable in Object Views)
- Confirmation: enabled, with message "Are you sure you want to change the status of {source_name}?"

---

### Action Types — Why Declarative Rules, Not Function-Backed

All three actions use **declarative Ontology rules** (modify/create object), not function-backed actions. The reasoning:

1. **Simplicity:** Each action modifies 1–2 properties on a single object. There is no multi-object logic, no derived field calculation, no conditional branching that would require code.
2. **Function rules are exclusive:** When you add a function rule, you cannot have any other Ontology rules in the same action. This means you'd need to implement even the simple property assignment in code, adding a function dependency for no benefit.
3. **Governance:** Declarative rules are auditable in the Ontology Manager UI. Function-backed rules require reading code in a separate repository to understand what the action does.

**When to switch to function-backed:** If a future action needs to create a transaction AND update the related source's `total_transactions` count in a single atomic operation, that cross-object logic requires a function-backed action. The "Record Manual Transaction" action could evolve into this.

---

### 6.4 "Categorize Bank Transaction"

| Attribute | Value |
|-----------|-------|
| **Target** | `BankTransaction` (single object) |
| **Rule type** | Modify object (declarative Ontology rules) |
| **Parameters** | `transaction` (object reference, required, hidden — auto-populated), `category` (string, required, dropdown: Groceries / Dining / Subscriptions / Housing / Transportation / Healthcare / Entertainment / Shopping / Utilities / Income / Transfer / Other) |
| **Edits** | Sets `category` to the selected value on the target transaction |
| **Where it appears** | Object detail panel button in Workshop; bulk action on transaction table selection |

**Why this action:**
- Auto-categorization (via PySpark string matching or Pipeline Builder LLM node) won't be 100% accurate. This action lets the user correct misclassified transactions.
- Demonstrates the human-in-the-loop pattern: AI classifies, human reviews and corrects. This is the exact pattern Palantir promotes for AIP workflows.
- The corrections feed back into the categorization pipeline as labeled training data — a feedback loop that improves auto-classification over time.

**Bulk action consideration:** Workshop supports multi-select on tables. Categorizing transactions one at a time is tedious when reviewing a month's worth of imports. Configure this action for bulk application: select 15 transactions → set category to "Dining" → apply to all. This requires no special setup — Workshop's multi-object action execution handles it natively when the action targets a single object.

---

### 6.5 "Record Bank Transaction"

| Attribute | Value |
|-----------|-------|
| **Target** | Creates a new `BankTransaction` |
| **Rule type** | Create object (declarative Ontology rules) |
| **Parameters** | `account` (Object Reference dropdown from `BankAccount` set), `date` (Date, default: today), `description` (String, required), `amount` (Double, required — negative for expenses, positive for income), `category` (String, dropdown), `transaction_id` (String, hidden, `generate_uuid`) |
| **Edits** | Creates a new `BankTransaction` with all mapped properties, `is_income` auto-set based on `amount > 0`, `is_transfer` defaulting to `false` |
| **Where it appears** | Workshop button (top-level); Operations tab |

**Why this action:**
- Handles cash transactions, Venmo/Zelle payments, or other events not captured in bank exports
- Same pattern as "Record Manual Transaction" (6.2) but for the Banking domain — demonstrates consistency across domains

---

### 6.6 "Flag Bank Transaction for Review"

| Attribute | Value |
|-----------|-------|
| **Target** | `BankTransaction` (single object) |
| **Rule type** | Modify object (declarative Ontology rules) |
| **Parameters** | `transaction` (object reference, required, hidden), `review_notes` (string, required) |
| **Edits** | Sets `flagged = true` and `review_notes` on the target transaction |
| **Where it appears** | Object detail panel button; transaction table row action |

**Why this action:**
- Mirrors "Flag Transaction for Review" (6.1) from the Bitcoin domain — identical pattern, different object type
- Useful for flagging unrecognized charges, potential fraud, or transactions that need recategorization
- The consistency of having the same flagging workflow across Bitcoin and Banking domains demonstrates a repeatable action pattern

---

## 7. Functions Layer

### Current Functions (no changes needed)

The existing 14 functions in `portfolio_metrics.py` operate on `List[BitcoinTransaction]` and remain valid. They compute:
- Per-transaction metrics: `get_amount_usd`, `get_amount_btc`, `get_total_return`, `get_total_return_percentage`
- Portfolio aggregates: `total_btc_holdings`, `total_portfolio_value`, `total_cost_basis`, `average_purchase_price`, `total_fees_paid`, `overall_return_percentage`
- Per-source profit: `total_profit_strike`, `total_profit_gemini`, `total_profit_coinbase`, `total_profit_exodus`, `total_profit_ibit`
- Live price: `get_current_price` (Kraken Ticker API)

### New Functions to Add

| Function | Input | Output | Purpose |
|----------|-------|--------|---------|
| `source_transaction_count` | `BitcoinSource` | Integer | Count of linked transactions (Workshop KPI on source detail panel) |
| `source_total_value` | `BitcoinSource` + live price | Float | Current USD value of all BTC purchased through this source |
| `snapshot_growth_since_inception` | `PortfolioSnapshot` | Float | % growth from first snapshot to this snapshot |
| `get_flagged_transactions` | `List[BitcoinTransaction]` | `List[BitcoinTransaction]` | Filter to only flagged transactions (Workshop filtered view) |

**Why these functions are minimal:** The `PortfolioSnapshot` object type precomputes most metrics in the PySpark transform (daily return, portfolio value, cost basis). Functions on snapshots should be thin — the heavy lifting is in the pipeline, not at query time. This follows the principle of pushing computation upstream.

### Functions Architecture Note

The existing per-source profit functions (`total_profit_strike`, `total_profit_gemini`, etc.) iterate over all transactions and filter by source name. With the new `BitcoinSource` object type and link, these could be refactored to:

```python
@function(sources=["BTCPriceData"])
def source_profit(source: BitcoinSource) -> float:
    current_price = get_current_price()
    total = 0.0
    for tx in source.sourceTransactions:
        if tx.type == "Buy":
            total += (tx.amount_btc * current_price) - tx.amount_usd
        elif tx.type == "Sell":
            total -= (tx.amount_btc * current_price) - tx.amount_usd
    return total
```

This replaces 5 nearly identical functions with 1 generic function that uses link traversal. **However**, link traversal in Python functions loads objects one-by-one (N+1 pattern). For 7 sources with ~900 total transactions this is fine, but be aware of the performance implication. The alternative is to continue passing `List[BitcoinTransaction]` and filtering in-memory, which avoids the link traversal cost. Keep both patterns available and choose based on the calling context (single source detail panel vs. full portfolio view).

### Cross-Domain Functions (new)

These functions operate across the Banking, Investment, and Bitcoin domains to power the unified financial analytics layer.

| Function | Input | Output | Purpose |
|----------|-------|--------|---------|
| `total_net_worth` | `NetWorthSnapshot` (latest) | Double | Current total net worth across all domains (Workshop headline KPI) |
| `monthly_savings_rate` | `MonthlyCashFlow` | Double | Savings rate for a given month as a percentage |
| `spending_by_category` | `List[BankTransaction]`, month filter | `Dict[str, float]` | Spending totals grouped by category for a given month (Workshop bar chart) |
| `btc_purchasing_power` | `Double` (USD amount) | Double | Converts any USD amount to BTC at the current live price (quick reference) |
| `personal_inflation_rate` | `List[PersonalInflationMetric]` | Double | Weighted average of all category YoY changes, weighted by `weight_in_budget` — the composite personal CPI |
| `account_balance` | `BankAccount` | Double | Reconstructed current balance from running sum of linked transactions |
| `investment_account_value` | `InvestmentAccount` | Double | Current market value of all positions in the account (requires live price data for holdings) |
| `purchase_impact` | `Double` (purchase amount), `Boolean` (is_financed), `Double` (monthly_payment), `Integer` (loan_term_months) | `Dict` | Computes impact on emergency fund, savings rate, and opportunity cost of a proposed purchase |
| `time_to_goal` | `Double` (goal_amount), `Double` (additional_monthly_income) | Integer (months) | Projects how many months until a net worth or savings target is reached, given current trajectory and optional income change |

**Architecture note:** Cross-domain functions need to query multiple object types (e.g., `purchase_impact` reads `MonthlyCashFlow` for current expenses and `NetWorthSnapshot` for current net worth). In Python functions, this means accepting multiple inputs or using Object Set queries. For complex multi-type queries, consider whether the function should accept precomputed values (simpler, faster) or query the ontology directly (more flexible, slower). Prefer precomputed inputs for Workshop KPIs where the backing data is already loaded; use ontology queries for AIP agent tool calls where the agent determines what to fetch.

---

## 8. Trade-offs and Design Decisions

### Decision 1: Separate `BitcoinSource` object type vs. denormalized source columns

| Option | Pros | Cons |
|--------|------|------|
| **Separate object type (chosen)** | Clean separation of concerns; source metadata updates independently; enables source-level actions; demonstrates multi-object ontology design | Requires a new dataset and link; small overhead for 7 objects |
| **Denormalized columns on BitcoinTransaction** | Simpler (no new dataset/link); all data in one place | Source metadata repeated on every transaction row; changing `is_active` requires reprocessing 900+ rows; doesn't demonstrate relational modeling |

**Decision rationale:** The portfolio has 7 sources and ~900 transactions. The overhead of a second object type is trivial. The benefit — demonstrating relational ontology modeling — is the single most referenced Foundry skill across tracked Palantir roles (per the TODO.md role impact matrix). This is the right trade-off for both the project and the portfolio.

### Decision 2: `PortfolioSnapshot` as precomputed dataset vs. derived properties

| Option | Pros | Cons |
|--------|------|------|
| **Precomputed PySpark dataset (chosen)** | Fast Workshop rendering (no runtime aggregation); demonstrates PySpark window functions; enables time-series charts natively | Adds a build step; data is 4 hours stale (build schedule) |
| **Derived properties on BitcoinTransaction** | Always fresh; no new dataset | Derived properties are beta, read-only, max 3 hops; can't do complex window functions; poor performance for time-series over 900+ rows at query time |
| **Functions computing daily snapshots at runtime** | Always fresh; no new dataset | Expensive: aggregating 900+ objects per request, multiplied by every day in the portfolio history; functions have ~4s fixed overhead per invocation |

**Decision rationale:** Portfolio snapshots are a **batch-computed analytical view**, not a real-time query. The 4-hour build schedule is more than sufficient for a personal savings tracker. PySpark window functions (running sum, daily return) are the correct tool and also the most asked-about technical skill in Palantir interviews.

### Decision 3: FK-based link vs. join table for Transaction → Source

| Option | Pros | Cons |
|--------|------|------|
| **Foreign key (chosen)** | No extra dataset; simple; matches the real-world cardinality (a transaction has exactly one source, forever) | Read-only (can't edit which source a transaction belongs to); no link metadata |
| **Join table** | Editable links; could add metadata to the relationship | Overkill — there's no scenario where a transaction's source changes; adds a dataset for no functional benefit |

**Decision rationale:** The question "which source did this transaction come from?" has exactly one answer that never changes. FK links express this constraint directly.

### Decision 4: Edit-only properties vs. new columns in the backing dataset

For `flagged` and `review_notes` on `BitcoinTransaction`:

| Option | Pros | Cons |
|--------|------|------|
| **Edit-only properties (chosen)** | No pipeline changes; writeback overlay keeps operational metadata separate from source data; clean separation of concerns | Properties don't appear in Contour queries against the raw dataset (only through the Ontology) |
| **New columns in backing dataset** | Available everywhere (Contour, raw SQL) | Requires Pipeline Builder changes; mixes operational state with source-of-truth data; pipeline rebuild could overwrite edits if not careful |

**Decision rationale:** `flagged` and `review_notes` are operational metadata added by users, not source data from exchanges. They should live in the writeback overlay, not the pipeline output. If Contour needs to query flagged transactions, use Object Set Service or a synced view — don't pollute the pipeline.

### Decision 5: Three separate transaction types vs. one unified `FinancialTransaction`

| Option | Pros | Cons |
|--------|------|------|
| **Separate types (chosen):** `BitcoinTransaction`, `BankTransaction`, `InvestmentTransaction` | Each type has a schema tailored to its domain (BTC has `amount_btc`/`exchange_rate`; investments have `symbol`/`quantity`/`price_per_unit`; banking has `category`/`is_income`/`is_transfer`). Respects the domain boundary principle. Allows independent pipeline development per domain. Each type can have domain-specific actions and functions | More object types to manage. Cross-domain queries require querying three types separately or through the `NetWorthSnapshot`/`MonthlyCashFlow` aggregation layer |
| **Unified `FinancialTransaction`** | Single object type to query. Simpler Workshop if all transactions appear in one table | Bloated schema with many null columns (BTC transactions don't have `symbol`; bank transactions don't have `quantity`). Violates domain boundaries. Forces a lowest-common-denominator property set. Makes domain-specific functions awkward (checking `if type == 'bitcoin'` everywhere) |
| **Interface + separate types** | Best of both worlds — domain-specific types with a shared interface for cross-domain functions | Python functions don't support interfaces yet. TypeScript v2 functions would be required. Adds complexity for a feature that's still in limited availability |

**Decision rationale:** The three transaction types have fundamentally different schemas. A Bitcoin buy has `amount_btc` and `exchange_rate`. A stock trade has `symbol`, `quantity`, and `price_per_unit`. A bank transaction has `category`, `is_income`, and `is_transfer`. Forcing these into one object type creates a wide, sparse table where most columns are null for most rows. Separate types are cleaner, and the cross-domain aggregation objects (`NetWorthSnapshot`, `MonthlyCashFlow`) provide the unified view where needed.

When Python functions gain interface support, the `FinancialTransaction` interface (shared properties: `date`, `amount_usd`, `btc_equivalent`) becomes viable as an abstraction layer for cross-domain functions without sacrificing domain-specific schemas.

### Decision 6: `btc_equivalent` as denormalized property vs. runtime function

| Option | Pros | Cons |
|--------|------|------|
| **Denormalized property (chosen)** | Precomputed once in PySpark; available instantly in Workshop charts and Contour; no function call overhead; enables BTC-denominated views natively | Stale if BTC price data is corrected retroactively (unlikely); slightly larger dataset |
| **Runtime function** | Always uses the latest price data; no storage overhead | Requires a join to the price dataset on every call; slow for large transaction sets; can't be used in Contour without wrapping in a derived property |

**Decision rationale:** The BTC-equivalent value is a historical fact — "what was this $50 dinner worth in BTC on the day I bought it?" The answer doesn't change. It's determined by the BTC closing price on that date, which is fixed once the day ends. Precomputing it in the PySpark transform (one join per build) is dramatically more efficient than computing it at query time (one join per function call). The same rationale applies to `btc_equivalent_spent` on `SpendingCategory` and `btc_denominated_change_pct` on `PersonalInflationMetric`.

### Decision 7: Credit card balance as negative `cash_balance` component vs. separate liability field

| Option | Pros | Cons |
|--------|------|------|
| **Separate `credit_card_balance` field on `NetWorthSnapshot` (chosen)** | Explicit; users can see exact CC debt; enables a "debt paydown" chart in Workshop; `total_net_worth` formula is transparent: `cash + investments + bitcoin - cc_balance` | One more field on the snapshot |
| **Net it into `cash_balance`** | Fewer fields; `cash_balance` represents net liquid position | Hides debt — a $5K checking balance with $3K CC debt shows as $2K "cash," which masks the liability. Users can't track debt paydown separately |

**Decision rationale:** Visibility into debt is more valuable than schema simplicity. The credit card balance is the only liability in the current scope, and surfacing it explicitly enables Workshop widgets like "credit card balance trend" and "days since last zero balance." If additional liabilities are added later (car loan, student loans), they follow the same pattern — separate fields on `NetWorthSnapshot`, subtracted from `total_net_worth`.

---

## 9. Step-by-Step Implementation Guide

### Phase 1: Create the `BitcoinSource` Backing Dataset

**Goal:** Produce a small derived dataset with one row per source, computed from the existing unified transaction data.

1. **Create a new PySpark transform** in `API_Data_Ingestion/transforms-python/src/myproject/datasets/` called `bitcoin_sources.py`
2. **Input:** `Bitcoin Transactions Dataset` (the existing unified output)
3. **Logic:**
   ```python
   from transforms.api import transform, Input, Output
   from pyspark.sql import functions as F

   @transform(
       output=Output("/path/to/Bitcoin_Sources"),
       transactions=Input("/path/to/Bitcoin_Transactions_Dataset")
   )
   def compute_sources(transactions, output):
       df = transactions.dataframe()

       sources = df.groupBy("source").agg(
           F.min("timestamp").alias("first_transaction_date"),
           F.max("timestamp").alias("last_transaction_date"),
           F.count("*").alias("total_transactions"),
           F.sum(F.when(F.col("type") == "Buy", F.col("amount_btc")).otherwise(0)).alias("total_btc_purchased"),
           F.sum(F.when(F.col("type") == "Buy", F.col("amount_usd")).otherwise(0)).alias("total_usd_spent"),
           F.lit(True).alias("is_active")
       ).withColumn(
           "source_id", F.lower(F.col("source"))
       ).withColumn(
           "source_name", F.col("source")
       ).withColumn(
           "source_type",
           F.when(F.col("source").isin("Gemini", "Coinbase", "Strike", "CashApp"), "exchange")
            .when(F.col("source").isin("Sparrow", "Exodus"), "wallet")
            .when(F.col("source") == "IBIT", "brokerage")
            .otherwise("unknown")
       )

       output.write_dataframe(sources)
   ```
4. **Register** the transform in `pipeline.py` via `my_pipeline.discover_transforms(datasets)`
5. **Build** the dataset and verify 7 rows (one per source)

### Phase 2: Create the `Daily_Portfolio_Snapshots` Backing Dataset

**Goal:** Produce a daily time-series dataset using PySpark window functions.

1. **Create** `daily_portfolio_snapshots.py` in the same datasets directory
2. **Inputs:** `Bitcoin Transactions Dataset` + `btc_15m_data_2018_to_2026` (for daily closing prices)
3. **Logic outline:**
   ```python
   from pyspark.sql import functions as F, Window

   # Generate a date spine from first transaction to today
   # For each date, compute:
   #   - cumulative BTC holdings (running sum of amount_btc for Buys, minus Sells)
   #   - cumulative cost basis (running sum of amount_usd for Buys)
   #   - daily closing price (from OHLC data, last 15-min candle of each day)
   #   - portfolio value = holdings × closing price
   #   - daily return % = (today's value - yesterday's value) / yesterday's value × 100
   #   - transaction count for the day
   #   - BTC bought and USD spent on that day

   window_to_date = Window.orderBy("date").rowsBetween(Window.unboundedPreceding, Window.currentRow)
   ```
4. **Build** and verify the output has one row per calendar day

### Phase 3: Register Object Types in Ontology Manager

1. **`BitcoinSource`:**
   - Open Ontology Manager → Create Object Type
   - Name: "Bitcoin Source", API name: `BitcoinSource`
   - Backing dataset: `Bitcoin_Sources`
   - Primary key: `source_id`
   - Title key: `source_name`
   - Map all properties from the dataset columns
   - Set status to `experimental`
   - Configure render hints per the table in Section 4

2. **`PortfolioSnapshot`:**
   - Create Object Type
   - Name: "Portfolio Snapshot", API name: `PortfolioSnapshot`
   - Backing dataset: `Daily_Portfolio_Snapshots`
   - Primary key: `snapshot_id`
   - Title key: `date`
   - Map all properties
   - Set status to `experimental`

3. **Update `BitcoinTransaction`:**
   - Add `flagged` as an edit-only Boolean property (no backing column)
   - Add `review_notes` as an edit-only String property
   - These properties will only be populated through writeback actions

### Phase 4: Create Link Types

1. **`BitcoinTransaction` → `BitcoinSource`:**
   - In Ontology Manager, open `BitcoinTransaction`
   - Add Link Type → target: `BitcoinSource`
   - Cardinality: many-to-one
   - Foreign key: `BitcoinTransaction.source` → `BitcoinSource.source_name`
   - API names: `transactionSource` (transaction side), `sourceTransactions` (source side)
   - Verify in Object Explorer: click a transaction → "Source" link shows the correct `BitcoinSource` object

2. **Verify bidirectional navigation:**
   - Open a `BitcoinSource` in Object Explorer
   - Confirm the "Transactions" linked objects tab shows the correct filtered list

### Phase 5: Create Action Types

1. **"Flag Transaction for Review":**
   - Create Action Type in Ontology Manager
   - Add parameter: `transaction` (Object Reference: `BitcoinTransaction`, required, hidden)
   - Add parameter: `review_notes` (String, required)
   - Add Modify Object rule: set `flagged = true`, `review_notes = {review_notes}` on `{transaction}`
   - Configure in Object Views: add as a button on the `BitcoinTransaction` detail panel

2. **"Create Bitcoin Transaction":**
   - Create Action Type
   - Add parameters: `source` (Object Reference dropdown from `BitcoinSource` set), `type` (String dropdown), `amount_btc` (Double), `amount_usd` (Double), `timestamp` (Timestamp, default: current), `notes` (String, optional), `id` (String, hidden, `generate_uuid` type class)
   - Add Create Object rule: create `BitcoinTransaction` with all mapped properties
   - Add submission criteria: `amount_btc > 0`

3. **"Update Source Status":**
   - Create Action Type
   - Add parameter: `source` (Object Reference: `BitcoinSource`, required, hidden)
   - Add parameter: `is_active` (Boolean, required)
   - Add Modify Object rule: set `is_active = {is_active}` on `{source}`

### Phase 6: Update Functions

1. **Regenerate the Ontology SDK** to include `BitcoinSource` and `PortfolioSnapshot` types
   - In the Functions repo, update `functions.json` SDK version if needed
   - Run the Foundry code assist / SDK generator
2. **Add new imports** in `portfolio_metrics.py`:
   ```python
   from ontology_sdk.ontology.objects import BitcoinTransaction, BitcoinSource, PortfolioSnapshot
   ```
3. **Add new functions** per the table in Section 7

### Phase 7: Validate End-to-End

1. **Object Explorer checks:**
   - Search for `BitcoinSource` → see 7 objects
   - Click "Strike" → see linked transactions
   - Click a transaction → see linked source
   - Search for `PortfolioSnapshot` → see daily snapshots
2. **Action checks:**
   - Flag a transaction → verify `flagged = true` and `review_notes` populated
   - Record a manual transaction → verify new object appears in Object Explorer
   - Update source status → verify `is_active` changed
3. **Workshop checks:**
   - KPI cards still work (existing functions unaffected)
   - Source-level views show correct data

---

## 10. Workshop Integration

The expanded ontology enables a multi-tab Workshop application spanning all three financial domains.

### Tab 1: Net Worth Dashboard (new — powered by `NetWorthSnapshot`)
- **Headline KPI cards:** Total Net Worth, Daily Change ($), Daily Change (%), Bitcoin Allocation %
- **Time-series area chart:** Net worth over time, stacked by component (cash, investments, Bitcoin)
- **Allocation pie chart:** Current split across cash/investments/Bitcoin
- **Milestone markers:** Horizontal lines at goal amounts (e.g., $100K, $250K)
- Date range filter propagating to all charts and all tabs

### Tab 2: Bitcoin Portfolio (existing, enhanced)
- Existing KPI cards (BTC Price, Holdings, Value, Profit, Return %)
- Transaction table with source filter backed by `BitcoinSource` object set
- "Flag for Review" button on selected transaction row
- Time-series chart: portfolio value vs. cost basis (from `PortfolioSnapshot`)
- Source breakdown bar chart (from `BitcoinSource`)

### Tab 3: Spending & Cash Flow (new — powered by `BankTransaction`, `SpendingCategory`, `MonthlyCashFlow`)
- **Monthly KPI cards:** Income, Expenses, Savings Rate %, Net Savings
- **Category bar chart:** Spending by category for the selected month (from `SpendingCategory`)
- **Cash flow trend:** Line chart of income vs. expenses over time (from `MonthlyCashFlow`)
- **Savings rate trend:** Line chart of `savings_rate_pct` over time
- **Transaction table:** Filterable by account, category, date range with "Categorize" action button
- Account selector backed by `BankAccount` object set

### Tab 4: Investments (new — powered by `InvestmentTransaction`, `InvestmentAccount`)
- **Account KPI cards:** Per-account value, total investment value, Roth IRA balance
- **Holdings table:** Current positions by symbol with quantity, cost basis, current value, return %
- **Transaction table:** Filterable by account, symbol, action type
- **Performance chart:** Investment value over time (reconstructed from transaction history)
- Account selector backed by `InvestmentAccount` object set

### Tab 5: Personal Inflation & BTC Purchasing Power (new — powered by `PersonalInflationMetric`)
- **Headline KPI:** Weighted Personal CPI vs. Official CPI
- **Category inflation bar chart:** YoY change % per category, color-coded (red = above CPI, green = below)
- **BTC purchasing power chart:** Dual-axis — USD spending (left axis) vs. BTC-equivalent spending (right axis) over time
- **Table:** All inflation metrics with `btc_denominated_change_pct` showing whether BTC appreciation outpaces personal inflation per category

### Tab 6: Operations (enhanced — powered by Action Types)
- "Record Manual Transaction" forms for both Bitcoin and Banking domains
- Flagged transactions table aggregating flagged items from both `BitcoinTransaction` and `BankTransaction`
- "Categorize Transaction" bulk action on uncategorized bank transactions
- Review workflow: select flagged transaction → view notes → resolve

### Object Set Filter Propagation

Workshop's filter widgets propagate across tabs using **linked object sets** and **shared date range filters**:
- A global date range filter in the Workshop header propagates to every tab
- Selecting a bank account in Tab 3 → filters transactions → updates category breakdown → filters `MonthlyCashFlow` to that account's contribution
- Selecting a date on the Net Worth chart (Tab 1) → shows that day's Bitcoin snapshot (Tab 2), bank transactions (Tab 3), and investment activity (Tab 4)
- Cross-domain navigation: clicking a net worth snapshot → linked `PortfolioSnapshot` for Bitcoin detail

---

## 11. Future Extensions

### 11.1 AIP Agent Layer — "Personal Financial Advisor" (Tier 3 Agentic Application)

The expanded ontology is the foundation for an AIP Agent embedded in the Workshop application. This agent operates across all three domains, answering natural-language financial questions grounded in the user's actual data.

**Agent configuration:**

| Component | Configuration |
|-----------|--------------|
| **Agent type** | Tier 3 — Agentic application (embedded in Workshop) |
| **LLM** | Model-agnostic via Agent Studio (GPT-4o, Claude, or Palantir-hosted) |
| **Object Query tools** | `BitcoinTransaction`, `BankTransaction`, `InvestmentTransaction`, `NetWorthSnapshot`, `MonthlyCashFlow`, `SpendingCategory`, `PersonalInflationMetric` — with accessible properties scoped per type to minimize token usage |
| **Action tools** | "Categorize Bank Transaction", "Flag Bank Transaction for Review", "Flag Transaction for Review" — user confirmation required for all writes |
| **Function tools** | `purchase_impact`, `time_to_goal`, `personal_inflation_rate`, `btc_purchasing_power`, `total_net_worth` |
| **Output variables** | `selected_date_range`, `highlighted_category`, `active_tab` — deterministic UI updates without LLM round-trips |
| **Request Clarification** | Enabled — agent asks follow-ups when queries are ambiguous |

**Example conversations the agent should handle:**

- "How much did I spend on dining last quarter?" → Object Query on `SpendingCategory` filtered by category and date
- "What's my savings rate trend over the last 6 months?" → Object Query on `MonthlyCashFlow`, last 6 records
- "What happens if I buy a $30K car with $5K down and a 60-month loan at 6.5%?" → Function call to `purchase_impact`
- "When should I make this purchase?" → Queries `MonthlyCashFlow` for cash flow patterns, identifies optimal window after next paycheck and before rent
- "What's my personal inflation rate?" → Function call to `personal_inflation_rate`
- "How much is my rent in BTC terms compared to last year?" → Object Query on `PersonalInflationMetric` for housing category, returns both USD and BTC-denominated change
- "Flag that weird $847 charge from last Tuesday" → Object Query to find matching transaction, then Action to flag it
- "Categorize all my Chick-fil-A transactions as dining" → Object Query to find matching transactions, then bulk Action to categorize

**Why Tier 3 (not Tier 2 or 4):**
- Tier 2 (task-specific agent) would work as a standalone chatbot but loses the Workshop context — the agent can't read which date range is selected, which account is filtered, or which tab is active.
- Tier 3 embeds the agent in Workshop with application state variables. The agent reads the current filter context (selected account, date range) and updates the UI (highlighting a category, switching tabs) through output variables. This is the full "agentic application" pattern.
- Tier 4 (automated agent) is the stretch goal — publishing the agent as a Function for scheduled weekly financial summaries via AIP Automate.

### 11.2 Chained Agent Automation (Tier 4)

A three-agent chain following the pattern from Palantir's DevCon 2 architecture:

1. **Agent 1 — Transaction Categorization (automated, scheduled):** Runs via AIP Automate when new bank transactions are ingested. Uses the Pipeline Builder LLM node to classify transactions by category. Flags low-confidence classifications for human review.
2. **Agent 2 — Anomaly Detection (automated, triggered):** Runs after categorization. Scans for unusual spending (transactions > 2x the category's monthly average), unrecognized merchants, or sudden spending spikes. Flags anomalies using the "Flag Bank Transaction for Review" action.
3. **Agent 3 — Weekly Financial Summary (automated, scheduled):** Runs weekly via AIP Automate. Compiles: net worth change, spending vs. budget by category, savings rate, flagged items requiring review. Sends a summary to inbox with a "Continue analysis" link that opens the Workshop application with the session pre-loaded.

**Why this matters for career:** This is the exact chained agent architecture Palantir demonstrates to enterprise clients — specialized agents handing off to each other, with humans intervening only at decision points. Implementing it for personal finance is a concrete, walkable demo for FDE interviews.

### 11.3 AIP Evals — Test Suite for the Financial Advisor Agent

Evaluation suites for the agent, leveraging QA experience:

| Test Case | Input | Expected Output | Evaluator |
|-----------|-------|-----------------|-----------|
| BTC holdings query | "How much Bitcoin do I own?" | Matches `total_btc_holdings` function output | Exact match |
| Savings rate query | "What's my savings rate?" | Matches latest `MonthlyCashFlow.savings_rate_pct` | Exact match |
| Purchase impact | "What if I buy a $40K car?" | Response mentions emergency fund impact, savings rate change, and opportunity cost | Rubric grader |
| Category spending | "How much did I spend on groceries in March?" | Matches `SpendingCategory` for groceries-YYYY-03 | Exact match |
| Ambiguous query | "How am I doing?" | Agent asks clarifying question (financial health? net worth? spending?) | LLM-as-judge |
| Cross-domain | "Compare my Bitcoin returns to my Schwab returns" | Response includes both domains with accurate return figures | Rubric grader |

### 11.4 Interface Abstraction

- Define a `FinancialTransaction` interface with shared properties: `date`, `amountUsd`, `btcEquivalent`
- `BitcoinTransaction`, `BankTransaction`, and `InvestmentTransaction` all implement this interface
- Functions written against the interface enable cross-domain queries without type-checking
- **Blocker:** Python functions do not yet support interfaces. Plan for TypeScript v2 functions if interfaces are needed at the function layer. The interface definition can be registered in the Ontology now and used in Workshop/Object Explorer even without function support.

### 11.5 Data Quality Object Type

- A `DataQualityReport` object type backed by a health check transform
- Validates: no duplicate transaction IDs across all three transaction types, no null amounts, date ranges within expected bounds, BTC price join completeness
- Link to `NetWorthSnapshot` by date — navigate from a snapshot to its quality metrics
- Action: "Acknowledge Data Issue" to mark known issues as reviewed

### 11.6 Tax Reporting

**FIFO Capital Gains (Bitcoin):**
- A `TaxLot` object type backed by a FIFO cost basis transform
- Link to `BitcoinTransaction` — each lot traces to the original Buy
- Properties: `acquisition_date`, `acquisition_cost`, `disposal_date`, `realized_gain`, `holding_period`, `is_long_term`

**Annual Tax Summary (cross-domain):**
- A `TaxYearSummary` object type with one row per tax year
- Aggregates: total W-2 income (from `BankTransaction` payroll deposits), total dividends (from `InvestmentTransaction`), total realized BTC gains (from `TaxLot`), total interest income (from savings/HYSA)
- Does not replace tax software — provides a consolidated view for tax prep

### 11.7 Scenario Modeling and Forecasting

**Monte Carlo Portfolio Projections:**
- A Foundry Function that runs 1,000+ simulations using historical volatility for each asset class (BTC, stocks, cash)
- Returns probability distributions: "70% chance portfolio is worth $X-$Y in 5 years"
- Surfaced in Workshop as a fan chart with confidence bands

**Income Strategy Modeling:**
- Functions that project net worth under different income scenarios: "What if I get a $130K job?" "What if I add $2K/month side income?"
- AIP agent can call these functions conversationally: the user asks "what if" questions, the agent queries current financial state and runs the projection

**Purchase Timing Optimization:**
- A function that analyzes cash flow patterns to recommend optimal purchase windows
- Factors: paycheck cadence, recurring bill dates, seasonal spending spikes, current cash buffer
- Returns: "Best window: March 15-20 (after paycheck, before rent, cash buffer at $X)"
