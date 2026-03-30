from transforms.api import transform, Input, Output
from pyspark.sql import functions as F, Window
from datetime import date

@transform(
    output=Output("ri.foundry.main.dataset.51a37154-2700-4849-8d16-b7f3a1c7ece1"),
    transactions=Input("ri.foundry.main.dataset.26f2f965-59ec-4b3b-b28e-f200fbe57746"),
    prices=Input("ri.foundry.main.dataset.815c935c-0eae-4e21-996e-225d76f0fbb0"),
)
def compute_daily_snapshots(transactions, prices, output):
    txn_df = transactions.dataframe()
    prices_df = prices.dataframe()

    # --- Step 1: Extract date from transactions (using actual column name) ---
    txn_df = txn_df.withColumn("date", F.to_date(F.col("Rounded_Timestamp")))

    # --- Step 2: Build a date spine from first transaction to today ---
    min_date = txn_df.agg(F.min("date")).collect()[0][0]
    num_days = (date.today() - min_date).days
    spark = txn_df.sparkSession
    date_spine = spark.range(0, num_days + 1) \
        .select(F.date_add(F.lit(min_date), F.col("id").cast("int")).alias("date"))

    # --- Step 3: Aggregate daily transaction activity ---
    daily_txns = txn_df.groupBy("date").agg(
        F.count("*").alias("transaction_count"),
        F.sum(
            F.when(F.col("Type") == "Buy", F.col("Amount_BTC")).otherwise(0)
        ).alias("btc_bought_today"),
        F.sum(
            F.when(F.col("Type") == "Buy", F.col("Amount_USD")).otherwise(0)
        ).alias("usd_spent_today"),
        # Net BTC change per day: Buys add, Sells subtract
        F.sum(
            F.when(F.col("Type") == "Buy", F.col("Amount_BTC"))
            .when(F.col("Type") == "Sell", -F.col("Amount_BTC"))
            .when(
                (F.col("Type") == "Send") & (F.col("Notes") != "Send to Cold Storage"), 
                -F.col("Amount_BTC")
            )
            .otherwise(0)
        ).alias("net_btc_change"),
        F.sum(
            F.when(F.col("Type") == "Buy", F.col("Amount_USD")).otherwise(0)
        ).alias("net_cost_basis_change"),
    )

    # --- Step 4: Join date spine with daily activity (fills in zero-transaction days) ---
    daily = date_spine.join(daily_txns, on="date", how="left").fillna(0, subset=[
        "transaction_count", "btc_bought_today", "usd_spent_today",
        "net_btc_change", "net_cost_basis_change"
    ])

    # --- Step 5: Compute cumulative holdings and cost basis using window ---
    window_to_date = Window.orderBy("date").rowsBetween(Window.unboundedPreceding, Window.currentRow)

    daily = daily \
        .withColumn("cumulative_btc_holdings", F.sum("net_btc_change").over(window_to_date)) \
        .withColumn("cumulative_cost_basis", F.sum("net_cost_basis_change").over(window_to_date))

    # --- Step 6: Join daily closing price from BTC_Daily_Prices (one row per day) ---
    daily_close = prices_df.select(
        F.to_date(F.col("date")).alias("date"),
        F.col("close").alias("closing_price_usd"),
    )

    daily = daily.join(daily_close, on="date", how="left")

    # --- Step 7: Compute portfolio value and daily return ---
    lag_window = Window.orderBy("date")

    daily = daily \
        .withColumn(
            "portfolio_value_usd",
            F.col("cumulative_btc_holdings") * F.col("closing_price_usd")
        ) \
        .withColumn(
            "prev_portfolio_value",
            F.lag("portfolio_value_usd", 1).over(lag_window)
        ) \
        .withColumn(
            "daily_return_pct",
            F.when(
                F.col("prev_portfolio_value").isNotNull() & (F.col("prev_portfolio_value") != 0),
                ((F.col("portfolio_value_usd") - F.col("prev_portfolio_value"))
                 / F.col("prev_portfolio_value")) * 100
            ).otherwise(F.lit(None))
        ) \
        .drop("prev_portfolio_value")

    # --- Step 8: Add primary key for ontology backing ---
    daily = daily.withColumn(
        "snapshot_id",
        F.date_format(F.col("date"), "yyyy-MM-dd")
    )

    output.write_dataframe(daily)