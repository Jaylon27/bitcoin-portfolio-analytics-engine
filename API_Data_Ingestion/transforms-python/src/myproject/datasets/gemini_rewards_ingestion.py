from transforms.api import transform, Output, Input, incremental
from transforms.external.systems import external_systems, Source
import json
import pandas as pd
import time
import hashlib
import hmac
import base64


@external_systems(
    btc_source=Source("ri.magritte..source.12e600a1-06fe-4817-9146-63bc5c0ad1ac"),
    geminiapi=Source("ri.magritte..source.f410e5fc-1232-4624-b547-7c3ca93df88e")
)
@incremental()
@transform(
    output=Output("ri.foundry.main.dataset.a92e62c3-aa29-4f55-9c4e-baba398dd039"),
    static_data=Input("ri.foundry.main.dataset.a921d66f-aa6b-419e-9268-636f0aba562e")
)
def gemini_rewards(output, static_data, geminiapi, btc_source):
    # --- 1. IDENTIFY EXISTING TRANSACTIONS (EID + FINGERPRINT) ---
    # static_df = static_data.dataframe().toPandas()
    existing_eids = set()
    # existing_fingerprints = set()
    last_static_ts = 0
    last_automated_ts = 0

    try:
        previous_df = output.dataframe().select("eid", "timestampms").toPandas()
        if not previous_df.empty:
            existing_eids = set(previous_df['eid'].astype(str).unique())
            last_automated_ts = previous_df['timestampms'].max()
    except:
        pass

    static_df = static_data.dataframe().toPandas()
    last_static_ts = 0

    if not static_df.empty:
        # Convert '2023-06-13T10:27:53' style strings to milliseconds
        static_ts_series = pd.to_datetime(static_df['Datetime'])
        last_static_ts = int(static_ts_series.max().timestamp() * 1000)

    start_threshold = max(last_static_ts, last_automated_ts)

    # --- 3. GEMINI API AUTH & FETCH ---
    api_key = geminiapi.get_secret("additionalSecretGeminiAPIKey")
    api_secret = geminiapi.get_secret("additionalSecretGeminiAPISecret").encode()

    path = "/v1/transfers"
    payload_dict = {
        "request": path,
        "nonce": int(time.time() * 1000),
        "account": "primary",
        "limit_transfers": 50
    }

    payload_json = json.dumps(payload_dict).encode()
    b64_payload = base64.b64encode(payload_json).decode()
    signature = hmac.new(api_secret, b64_payload.encode(), hashlib.sha384).hexdigest()

    headers = {
        "Content-Type": "text/plain",
        "X-GEMINI-APIKEY": api_key,
        "X-GEMINI-PAYLOAD": b64_payload,
        "X-GEMINI-SIGNATURE": signature,
    }

    gemini_client = geminiapi.get_https_connection().get_client()
    response = gemini_client.post(f"https://api.gemini.com{path}", headers=headers)

    if response.status_code != 200:
        raise Exception(f"Gemini API Error {response.status_code}: {response.text}")

    data = response.json()

    # --- 4. FILTER NEW REWARDS ONLY (USING EID & FINGERPRINT) ---
    new_rewards_to_process = []
    for item in data:
        if item.get("type") == "Reward":
            ts = item.get("timestampms", 0)
            current_eid = str(item.get("eid", ""))

            # Check threshold, EID, AND Fingerprint to ensure zero duplicates
            if ts >= start_threshold:
                if current_eid not in existing_eids:
                    new_rewards_to_process.append(item)

    if not new_rewards_to_process:
        return

    # --- 5. HISTORICAL BTC PRICE LOOKUP ---
    btc_conn = btc_source.get_https_connection()
    btc_client = btc_conn.get_client()
    final_output_rows = []

    for reward in new_rewards_to_process:
        timestamp_s = int(reward.get("timestampms") / 1000)
        ohlc_url = f"{btc_conn.url}/0/public/OHLC?pair=XXBTZUSD&interval=1&since={timestamp_s}"

        try:
            price_res = btc_client.get(ohlc_url).json()
            reward['Exchange_Rate'] = float(price_res["result"]["XXBTZUSD"][0][4])
        except:
            reward['Exchange_Rate'] = None

        final_output_rows.append(reward)
        time.sleep(0.1)

    # --- 6. APPEND NEW DATA ---
    output.write_pandas(pd.DataFrame(final_output_rows))
