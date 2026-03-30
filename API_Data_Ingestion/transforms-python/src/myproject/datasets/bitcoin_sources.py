from transforms.api import transform, Input, Output
from pyspark.sql import functions as F


@transform(
    output=Output("ri.foundry.main.dataset.ad2b098c-6061-4ab0-96d6-b4c32bae3396"),
    transactions=Input("ri.foundry.main.dataset.26f2f965-59ec-4b3b-b28e-f200fbe57746")
   )
def compute_sources(transactions, output):
    df = transactions.dataframe()

    sources = df.groupBy("Source").agg(
        F.min("Rounded_Timestamp").alias("First_Transaction_Date"),
        F.max("Rounded_Timestamp").alias("Last_Transaction_Date"),
        F.count("*").alias("Total_Transactions"),
        F.sum(F.when(F.col("Type") == "Buy", F.col("Amount_BTC")).otherwise(0)).alias("Total_BTC_Purchased"),
        F.sum(F.when(F.col("Type") == "Buy", F.col("Amount_USD")).otherwise(0)).alias("Total_USD_Spent"),
        F.lit(True).alias("Is_Active")
    ).withColumn(
        "Source_ID", F.lower(F.col("Source"))
    ).withColumn(
        "Source_Name", F.col("Source")
    ).withColumn(
        "Source_Type",
        F.when(F.col("Source").isin("Gemini", "Coinbase", "Strike", "CashApp"), "Exchange")
        .when(F.col("Source").isin("Sparrow", "Exodus"), "Wallet")
        .when(F.col("Source") == "IBIT", "Brokerage")
        .otherwise("Unknown")
    )

    output.write_dataframe(sources)
