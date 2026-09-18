import time
import requests
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

RAW_DIR = Path("data/raw")
API_KEY = os.getenv("BSCSCAN_API_KEY")
BASE_URL = "https://api.bscscan.com/api"

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


def get_creation_info(address):
    params = {
        "module": "contract",
        "action": "getcontractcreation",
        "contractaddresses": address,
        "apikey": API_KEY,
    }
    resp = requests.get(BASE_URL, params=params, timeout=15)
    data = resp.json()
    if data.get("status") == "1" and data.get("result"):
        r = data["result"][0]
        return r.get("contractCreator"), r.get("txHash")
    return None, None


def get_tx_details(tx_hash):
    params = {
        "module": "proxy",
        "action": "eth_getTransactionByHash",
        "txhash": tx_hash,
        "apikey": API_KEY,
    }
    resp = requests.get(BASE_URL, params=params, timeout=15)
    result = resp.json().get("result")
    if not result:
        return None, None
    gas_price = int(result.get("gasPrice", "0x0"), 16)
    block_number = int(result.get("blockNumber", "0x0"), 16)
    return gas_price, block_number


def get_tx_receipt_gas_used(tx_hash):
    params = {
        "module": "proxy",
        "action": "eth_getTransactionReceipt",
        "txhash": tx_hash,
        "apikey": API_KEY,
    }
    resp = requests.get(BASE_URL, params=params, timeout=15)
    result = resp.json().get("result")
    if not result:
        return None
    return int(result.get("gasUsed", "0x0"), 16)


def eth_call(address, selector):
    params = {
        "module": "proxy",
        "action": "eth_call",
        "to": address,
        "data": selector,
        "tag": "latest",
        "apikey": API_KEY,
    }
    resp = requests.get(BASE_URL, params=params, timeout=15)
    return resp.json().get("result")


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


def get_token_basic_info(address):
    symbol = decode_string(eth_call(address, FUNC_SELECTORS["symbol"]))
    time.sleep(0.25)
    decimals = decode_int(eth_call(address, FUNC_SELECTORS["decimals"]))
    time.sleep(0.25)
    total_supply = decode_int(eth_call(address, FUNC_SELECTORS["totalSupply"]))
    time.sleep(0.25)
    return symbol, decimals, total_supply


def fetch_scam_token_data(addresses, delay=0.25):
    rows = []
    for i, address in enumerate(addresses):
        print(f"[{i + 1}/{len(addresses)}] fetching {address}")
        creator, tx_hash = get_creation_info(address)
        time.sleep(delay)

        gas_price, block_number = (None, None)
        gas_used = None
        if tx_hash:
            gas_price, block_number = get_tx_details(tx_hash)
            time.sleep(delay)
            gas_used = get_tx_receipt_gas_used(tx_hash)
            time.sleep(delay)

        symbol, decimals, total_supply = get_token_basic_info(address)

        rows.append({
            "address": address,
            "symbol": symbol,
            "name": None,
            "decimals": decimals,
            "total_supply": total_supply,
            "tx_hash": tx_hash,
            "block_number": block_number,
            "from_tx": creator,
            "gas_price": gas_price,
            "gas_used": gas_used,
            "value": None,
            "creator": creator,
        })

    return pd.DataFrame(rows)


def main():
    if not API_KEY:
        print("BSCSCAN_API_KEY not set — aborting")
        return

    addresses = get_bsc_scam_addresses()
    print(f"Fetching live data for {len(addresses)} confirmed BSC rug-pull addresses")

    df = fetch_scam_token_data(addresses)
    out_path = RAW_DIR / "scam_tokens_live.csv"
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df)} rows to {out_path}")


if __name__ == "__main__":
    main()