import time
import pandas as pd
import requests
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

LABELED_DIR = Path("data/labeled")
RPC_URL = os.getenv("MEGANODE_RPC_URL")

OWNER_SELECTOR = "0x8da5cb5b"
GET_PAIR_SELECTOR = "0xe6a43905"
PANCAKE_FACTORY = "0xca143ce32fe78f1f7019d7d551a6402fc5350c73"
WBNB = "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c"
ZERO_ADDRESS = "0x" + "0" * 40


def load_labeled_tokens():
    return pd.read_csv(LABELED_DIR / "labeled_tokens.csv", low_memory=False)


def add_offline_features(df):
    df["supply_log"] = df["total_supply"].apply(lambda x: len(str(int(x))) if pd.notna(x) else 0)
    return df


def rpc_call(method, params, retries=6, timeout=30, backoff=4):
    payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    for attempt in range(retries):
        try:
            resp = requests.post(RPC_URL, json=payload, timeout=timeout)
            return resp.json().get("result")
        except requests.exceptions.RequestException as e:
            wait = backoff * (attempt + 1)
            print(f"  request failed ({e}) — retry {attempt + 1}/{retries} in {wait}s")
            time.sleep(wait)
    return None


def pad_address(address):
    return address.lower().replace("0x", "").zfill(64)


def decode_address(hex_result):
    if not hex_result or hex_result == "0x":
        return None
    try:
        return "0x" + hex_result[-40:]
    except Exception:
        return None


def owner_not_renounced(address, delay):
    result = rpc_call("eth_call", [{"to": address, "data": OWNER_SELECTOR}, "latest"])
    time.sleep(delay)
    owner = decode_address(result)
    if owner is None:
        return None
    return int(owner.lower() != ZERO_ADDRESS)


def has_liquidity_pool_live(address, delay):
    data = GET_PAIR_SELECTOR + pad_address(address) + pad_address(WBNB)
    result = rpc_call("eth_call", [{"to": PANCAKE_FACTORY, "data": data}, "latest"])
    time.sleep(delay)
    pair = decode_address(result)
    if pair is None:
        return None
    return int(pair.lower() != ZERO_ADDRESS)


def enrich_with_onchain(df, legit_sample_size=500, delay=0.3):
    if not RPC_URL:
        print("MEGANODE_RPC_URL not set — skipping live enrichment")
        return df

    scam_rows = df[df["label"] == 1]
    legit_rows = df[df["label"] == 0].sample(n=legit_sample_size, random_state=42)
    subset = pd.concat([scam_rows, legit_rows]).copy()

    print(f"Enriching {len(scam_rows)} scam rows and {len(legit_rows)} legit rows")

    owner_flags = []
    lp_flags = []
    for i, row in subset.iterrows():
        address = row["address"]
        try:
            owner_flags.append(owner_not_renounced(address, delay))
        except Exception as e:
            print(f"owner check failed for {address}: {e}")
            owner_flags.append(None)

        try:
            lp_flags.append(has_liquidity_pool_live(address, delay))
        except Exception as e:
            print(f"liquidity check failed for {address}: {e}")
            lp_flags.append(None)

    subset["owner_not_renounced"] = owner_flags
    subset["has_liquidity_pool_live"] = lp_flags

    df = df.merge(
        subset[["address", "owner_not_renounced", "has_liquidity_pool_live"]],
        on="address",
        how="left",
    )
    return df


def main(live=False, legit_sample_size=500):
    df = load_labeled_tokens()
    df = add_offline_features(df)

    if live:
        df = enrich_with_onchain(df, legit_sample_size=legit_sample_size)

    out_path = LABELED_DIR / "training_data.csv"
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df)} rows to {out_path}")


if __name__ == "__main__":
    main(live=True)
