import time
import requests
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

RAW_DIR = Path("data/raw")
RPC_URL = os.getenv("MEGANODE_RPC_URL")
OUT_PATH = RAW_DIR / "scam_tokens_live.csv"

FUNC_SELECTORS = {
    "symbol": "0x95d89b41",
    "decimals": "0x313ce567",
    "totalSupply": "0x18160ddd",
}


def get_bsc_scam_addresses():
    df = pd.read_csv(RAW_DIR / "rugpull_dataset.csv", low_memory=False)
    df.columns = [c.strip().lower() for c in df.columns]
    df = df[df["chain"].str.upper() == "BSC"]
    return df["address"].str.lower().str.strip().tolist()


def rpc_call(method, params, retries=4, timeout=30, backoff=3):
    payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    for attempt in range(retries):
        try:
            resp = requests.post(RPC_URL, json=payload, timeout=timeout)
            data = resp.json()
            return data.get("result")
        except requests.exceptions.RequestException as e:
            wait = backoff * (attempt + 1)
            print(f"  request failed ({e}) — retry {attempt + 1}/{retries} in {wait}s")
            time.sleep(wait)
    print("  giving up on this request after retries")
    return None


def get_code(address):
    return rpc_call("eth_getCode", [address, "latest"])


def eth_call(address, selector):
    return rpc_call("eth_call", [{"to": address, "data": selector}, "latest"])


def get_transaction_count(address):
    result = rpc_call("eth_getTransactionCount", [address, "latest"])
    return int(result, 16) if result else None


def decode_string(hex_result):
    if not hex_result or hex_result == "0x":
        return None
    try:
        raw = bytes.fromhex(hex_result[2:])
        return raw[64:].split(b"\x00")[0].decode("utf-8", errors="ignore").strip()
    except Exception:
        return None


def decode_int(hex_result):
    if not hex_result or hex_result == "0x":
        return None
    try:
        return int(hex_result, 16)
    except Exception:
        return None


def fetch_one(address, delay):
    code = get_code(address)
    is_contract = bool(code and code != "0x")
    time.sleep(delay)

    symbol = decimals = total_supply = None
    if is_contract:
        symbol = decode_string(eth_call(address, FUNC_SELECTORS["symbol"]))
        time.sleep(delay)
        decimals = decode_int(eth_call(address, FUNC_SELECTORS["decimals"]))
        time.sleep(delay)
        total_supply = decode_int(eth_call(address, FUNC_SELECTORS["totalSupply"]))
        time.sleep(delay)

    return {
        "address": address,
        "is_contract": is_contract,
        "symbol": symbol,
        "name": None,
        "decimals": decimals,
        "total_supply": total_supply,
        "tx_hash": None,
        "block_number": None,
        "from_tx": None,
        "gas_price": None,
        "gas_used": None,
        "value": None,
        "creator": None,
    }


def load_existing():
    if OUT_PATH.exists():
        df = pd.read_csv(OUT_PATH, low_memory=False)
        return df, set(df["address"].str.lower().str.strip())
    return pd.DataFrame(), set()


def fetch_scam_token_data(addresses, delay=0.3):
    existing_df, done_addresses = load_existing()
    rows = existing_df.to_dict("records")

    remaining = [a for a in addresses if a not in done_addresses]
    print(f"{len(done_addresses)} already fetched, {len(remaining)} remaining")

    for i, address in enumerate(remaining):
        print(f"[{i + 1}/{len(remaining)}] fetching {address}")
        try:
            row = fetch_one(address, delay)
            rows.append(row)
        except Exception as e:
            print(f"  skipping {address} after repeated failure: {e}")
            continue

        pd.DataFrame(rows).to_csv(OUT_PATH, index=False)

    return pd.DataFrame(rows)


def main():
    if not RPC_URL:
        print("MEGANODE_RPC_URL not set — aborting")
        return

    addresses = get_bsc_scam_addresses()
    print(f"Target: {len(addresses)} confirmed BSC rug-pull addresses")

    df = fetch_scam_token_data(addresses)
    print(f"Saved {len(df)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()