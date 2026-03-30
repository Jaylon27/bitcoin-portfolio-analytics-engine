# Bitcoin Portfolio Analytics Engine — TODO

Enhancements to take this project from a strong data pipeline to a full-stack Foundry application.

---

## Tier 1: High-Impact Additions (Do These First)

### 1. Add a PySpark Transform
- [ ] Write a PySpark transform that computes a **Daily Portfolio Snapshot** dataset
- [ ] For each day, calculate: total holdings, total cost basis, portfolio value (using OHLC join data), daily return
- [ ] Use PySpark window functions (`Window.partitionBy().orderBy()`), running aggregations over full transaction history
- [ ] Output a new `Daily_Portfolio_Snapshots` dataset that feeds richer Contour analytics
- [ ] **Skills demonstrated:** PySpark, window functions, derived analytical datasets
- [ ] **Why it matters:** PySpark is listed as required/strongly preferred in nearly every Palantir role

### 2. Expand the Ontology with Additional Object Types and Links
- [ ] Create **`BitcoinSource`** Object Type — one object per source (Strike, Gemini, Coinbase, etc.)
  - Properties: `source_name`, `first_transaction_date`, `total_transactions`, `total_btc_purchased`, `is_active`
  - Back with a small derived dataset
- [ ] Create **`PortfolioSnapshot`** Object Type — backed by the Daily Portfolio Snapshots dataset
  - Properties: `date`, `total_holdings_btc`, `portfolio_value_usd`, `cost_basis_usd`, `daily_return_pct`
- [ ] Add **Link types:** `BitcoinTransaction` → `BitcoinSource` (many-to-one)
- [ ] Enable navigation from transaction to source and vice versa in Workshop/Object Explorer
- [ ] **Skills demonstrated:** Ontology design, data modeling, multi-object ontologies with typed relationships
- [ ] **Why it matters:** Ontology design is the single most referenced Foundry skill across tracked Palantir roles

### 3. Implement Action Types (Writeback)
- [ ] **"Flag Transaction for Review"** — Action on `BitcoinTransaction` that sets a `flagged` boolean and writes `review_notes`. Surface in Workshop as a button on the object detail panel.
- [ ] **"Record Manual Transaction"** — Action that creates a new `BitcoinTransaction` by writing to a backing dataset. Inputs: source, type, amount_btc, amount_usd, timestamp, notes.
- [ ] **"Update Source Status"** — Action on `BitcoinSource` to mark a source as active/inactive.
- [ ] **Skills demonstrated:** Writeback, operational workflows, Action Types
- [ ] **Why it matters:** Turns Workshop from read-only dashboard into an operational application — exactly the Palantir pitch ("decision-making software, not just analytics")

---

## Tier 2: Strong Differentiators

### 4. Add a Second API Integration (Coinbase or Strike)
- [ ] Add a second automated API ingestion to show the architecture is generalizable
- [ ] **Option A: Coinbase** — Uses OAuth2 (different auth paradigm from Gemini's HMAC), shows breadth
- [ ] **Option B: Strike** — Moves a CSV-loader source to fully automated, shows a real migration story
- [ ] Write as a new transform in `API_Data_Ingestion/transforms-python/src/myproject/datasets/`
- [ ] Wire into `pipeline.py`
- [ ] **Skills demonstrated:** Integration patterns, multiple API auth paradigms

### 5. Data Quality / Health Checks Transform
- [ ] Write a transform that validates no duplicate EIDs across the unified dataset
- [ ] Check for null exchange rates after the LEFT JOIN (should be zero)
- [ ] Verify all timestamps fall within expected ranges
- [ ] Output a `Data_Quality_Report` dataset with pass/fail metrics per run
- [ ] **Skills demonstrated:** Data governance, pipeline reliability
- [ ] **Why it matters:** Data governance is explicitly listed in shared skills for Category 4 roles

### 6. Tax / Capital Gains Calculation (FIFO Cost Basis)
- [ ] Implement **FIFO (First-In-First-Out)** cost basis tracking
- [ ] Calculate realized capital gains for each Sell transaction
- [ ] Distinguish short-term vs. long-term capital gains (held > 1 year)
- [ ] Output a `Capital_Gains_Report` dataset
- [ ] **Skills demonstrated:** Non-trivial business logic translation on Foundry
- [ ] **Why it matters:** Shows ability to translate business requirements into platform features (core FDE work)

### 7. Multi-Tab Workshop with Charts
- [ ] **Portfolio Overview** tab — time-series charts powered by new `PortfolioSnapshot` objects
- [ ] **Source Breakdown** tab — per-source metrics using `BitcoinSource` objects
- [ ] **Data Quality** tab — surface health check results from the Data Quality transform
- [ ] Object Set filters that propagate across tabs
- [ ] **Skills demonstrated:** Full Workshop application design, multi-view layouts

---

## Tier 3: Polish and Narrative

### 8. TypeScript Functions
- [ ] Port a few simpler functions to TypeScript in a new functions repo (e.g., `get_current_price`, `total_cost_basis`)
- [ ] Even a small set shows ability to work in both Python and TypeScript on the platform
- [ ] **Skills demonstrated:** TypeScript (nice-to-have in several target roles)

### 9. Document Ontology Design Decisions
- [ ] Create `ONTOLOGY_DESIGN.md` in docs folder
- [ ] Explain why these Object Types were chosen
- [ ] Document how link types model real relationships
- [ ] List Action Types and their rationale
- [ ] Describe trade-offs considered (e.g., denormalization vs. linked objects)
- [ ] **Why it matters:** Ontology design is the most common Foundry interview topic — having a written rationale shows architecture-level thinking

### 10. Expand to Multi-Asset (Stretch Goal)
- [ ] Generalize from BTC-only to multi-asset (ETH, SOL, or stocks via IBIT)
- [ ] Add `asset` as a dimension to the unified schema
- [ ] Show the ontology and functions handle multiple asset classes gracefully
- [ ] **Skills demonstrated:** Scalable architecture, generalizable data modeling

---

## Role Impact Matrix

| Enhancement | Skills Demonstrated | Roles It Helps |
|---|---|---|
| PySpark transform | PySpark, window functions, derived datasets | All Palantir roles (mandatory skill) |
| Multi-object Ontology + Links | Ontology design, data modeling | FDE, Implementation Engineer, Foundry Engineer |
| Action Types | Writeback, operational workflows | FDE, Implementation Engineer |
| Second API integration | Integration patterns, different auth | Foundry Engineer, Data Engineer |
| Data quality checks | Data governance, pipeline reliability | All Palantir + DevOps roles |
| FIFO capital gains | Business logic translation | FDE, Data SME/Architect |
| Multi-tab Workshop | Workshop application building | FDE, Implementation Engineer |
| TypeScript Functions | TypeScript (nice-to-have) | FDE, Foundry Engineer |
| Ontology design doc | Architecture communication | All Palantir roles (interview prep) |
| Multi-asset expansion | Scalable architecture | Data SME/Architect, Foundry Engineer |
