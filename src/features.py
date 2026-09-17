import time
import pandas as pd
import requests
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

LABELED_DIR = Path("data/labeled")
API_KEY = os.getenv("BSCSCAN_API_KEY")
BASE_URL = "https://api.bscscan.com/api"


def load_labeled_tokens():
    return pd.read_csv(LABELED_DIR / "labeled_tokens.csv")


def add_offline_features(df):
    df["supply_log"] = df["total_supply"].apply(lambda x: len(str(int(x))) if pd.notna(x) else 0)
    df["gas_price_gwei"] = df["gas_price"] / 1e9
    df["low_gas_flag"] = (df["gas_price_gwei"] < 5).astype(int)
    df["has_liquidity_pool"] = df["has_liquidity_pool"].fillna(False).astype(int)
    return df


def get_wallet_first_tx_timestamp(address):
    params = {
        "module": "account",
        "action": "txlist",
        "address": address,
        "startblock": 0,
        "endblock": 99999999,
        "page": 1,
        "offset": 1,
        "sort": "asc",
        "apikey": API_KEY,
    }
    resp = requests.get(BASE_URL, params=params, timeout=15)
    data = resp.json()
    if data.get("status") == "1" and data.get("result"):
        return int(data["result"][0]["timeStamp"])
    return None


def get_contract_source(address):
    params = {
        "module": "contract",
        "action": "getsourcecode",
        "address": address,
        "apikey": API_KEY,
    }
    resp = requests.get(BASE_URL, params=params, timeout=15)
    data = resp.json()
    if data.get("status") == "1" and data.get("result"):
        return data["result"][0].get("SourceCode", "")
    return ""


def flag_owner_permissions(source_code):
    if not source_code:
        return None
    lowered = source_code.lower()
    has_mint = "function mint" in lowered
    has_pause = "function pause" in lowered or "tradingenabled" in lowered
    has_blacklist = "blacklist" in lowered
    return int(has_mint or has_pause or has_blacklist)

def enrich_with_onchain(df, limit=50, delay=0.25):
    if not API_KEY:
        print("BSCSCAN_API_KEY not set — skipping live enrichment")
        return df

    subset = df.head(limit).copy()
    wallet_ages = []
    owner_flags = []

    for i, row in subset.iterrows():
        address = row["address"]
        try:
            first_tx = get_wallet_first_tx_timestamp(address)
            wallet_ages.append(first_tx)
        except Exception as e:
            print(f"wallet age fetch failed for {address}: {e}")
            wallet_ages.append(None)
        time.sleep(delay)

        try:
            source = get_contract_source(address)
            owner_flags.append(flag_owner_permissions(source))
        except Exception as e:
            print(f"contract source fetch failed for {address}: {e}")
            owner_flags.append(None)
        time.sleep(delay)

    subset["creator_first_tx_ts"] = wallet_ages
    subset["risky_owner_permissions"] = owner_flags

    df = df.merge(
        subset[["address", "creator_first_tx_ts", "risky_owner_permissions"]],
        on="address",
        how="left",
    )
    return df


def main(live=False, limit=50):
    df = load_labeled_tokens()
    df = add_offline_features(df)

    if live:
        df = enrich_with_onchain(df, limit=limit)

    out_path = LABELED_DIR / "training_data.csv"
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df)} rows to {out_path}")


if __name__ == "__main__":
    main(live=False)