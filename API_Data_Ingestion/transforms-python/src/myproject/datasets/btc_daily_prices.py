from transforms.api import transform, Output, incremental
from transforms.external.systems import external_systems, Source
import pandas as pd
import time
from datetime import datetime, timezone

FIRST_TRANSACTION_EPOCH = 1610064000  # Jan 8, 2021 00:00:00 UTC


@external_systems(
    btc_source=Source("ri.magritte..source.12e600a1-06fe-4817-9146-63bc5c0ad1ac"),
)
@incremental()
@transform(
    output=Output("ri.foundry.main.dataset.815c935c-0eae-4e21-996e-225d76f0fbb0"),
)
def btc_daily_prices(output, btc_source):
    fetch_since = FIRST_TRANSACTION_EPOCH

    try:
        previous_df = output.dataframe().select("timestamp").toPandas()
        if not previous_df.empty:
            fetch_since = int(previous_df["timestamp"].max())
    except Exception:
        pass

    btc_conn = btc_source.get_https_connection()
    btc_client = btc_conn.get_client()

    all_candles = []
    current_since = fetch_since
    existing_timestamps = set()

    try:
        prev = output.dataframe().select("timestamp").toPandas()
        existing_timestamps = set(prev["timestamp"].astype(int))
    except Exception:
        pass

    while True:
        url = f"{btc_conn.url}/0/public/OHLC?pair=XXBTZUSD&interval=1440&since={current_since}"
        response = btc_client.get(url)

        if response.status_code != 200:
            raise Exception(f"Kraken API Error {response.status_code}: {response.text}")

        data = response.json()

        if data.get("error"):
            raise Exception(f"Kraken API Error: {data['error']}")

        candles = data["result"]["XXBTZUSD"]

        if not candles:
            break

        # Last entry is the current incomplete candle per Kraken docs
        complete_candles = candles[:-1]

        for c in complete_candles:
            ts = int(c[0])
            if ts not in existing_timestamps:
                all_candles.append({
                    "timestamp": ts,
                    "date": datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"),
                    "open": float(c[1]),
                    "high": float(c[2]),
                    "low": float(c[3]),
                    "close": float(c[4]),
                    "vwap": float(c[5]),
                    "volume": float(c[6]),
                    "trade_count": int(c[7]),
                })
                existing_timestamps.add(ts)

        next_since = data["result"].get("last", 0)

        if next_since <= current_since or len(complete_candles) < 2:
            break

        current_since = next_since
        time.sleep(1)

    if not all_candles:
        return

    output.write_pandas(pd.DataFrame(all_candles))
