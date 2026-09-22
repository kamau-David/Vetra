import time
import requests
import joblib
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os

load_dotenv()

RPC_URL = os.getenv("MEGANODE_RPC_URL")
MODEL_PATH = Path("models/vetra_model.joblib")

PANCAKE_FACTORY = "0xca143ce32fe78f1f7019d7d551a6402fc5350c73"
WBNB = "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c"
ZERO_ADDRESS = "0x" + "0" * 40

SELECTORS = {
    "symbol": "0x95d89b41",
    "totalSupply": "0x18160ddd",
    "owner": "0x8da5cb5b",
    "getPair": "0xe6a43905",
}

app = FastAPI(title="Vetra")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_bundle = joblib.load(MODEL_PATH)
model = _bundle["model"]
feature_columns = _bundle["features"]


class AddressRequest(BaseModel):
    address: str


def rpc_call(method, params, retries=4, timeout=20, backoff=3):
    payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    for attempt in range(retries):
        try:
            resp = requests.post(RPC_URL, json=payload, timeout=timeout)
            return resp.json().get("result")
        except requests.exceptions.RequestException:
            time.sleep(backoff * (attempt + 1))
    return None


def pad_address(address):
    return address.lower().replace("0x", "").zfill(64)


def decode_address(hex_result):
    if not hex_result or hex_result == "0x":
        return None
    return "0x" + hex_result[-40:]


def decode_int(hex_result):
    if not hex_result or hex_result == "0x":
        return None
    try:
        return int(hex_result, 16)
    except ValueError:
        return None


def get_code(address):
    return rpc_call("eth_getCode", [address, "latest"])


def eth_call(to, data):
    return rpc_call("eth_call", [{"to": to, "data": data}, "latest"])


def get_total_supply(address):
    return decode_int(eth_call(address, SELECTORS["totalSupply"]))


def get_owner_not_renounced(address):
    owner = decode_address(eth_call(address, SELECTORS["owner"]))
    if owner is None:
        return None
    return int(owner.lower() != ZERO_ADDRESS)


def get_has_liquidity_pool(address):
    data = SELECTORS["getPair"] + pad_address(address) + pad_address(WBNB)
    pair = decode_address(eth_call(PANCAKE_FACTORY, data))
    if pair is None:
        return None
    return int(pair.lower() != ZERO_ADDRESS)


def build_feature_row(address):
    total_supply = get_total_supply(address)
    supply_log = len(str(total_supply)) if total_supply else 0
    has_liquidity_pool_live = get_has_liquidity_pool(address) or 0
    owner_not_renounced = get_owner_not_renounced(address)

    return {
        "supply_log": supply_log,
        "has_liquidity_pool_live": has_liquidity_pool_live,
        "owner_not_renounced": owner_not_renounced if owner_not_renounced is not None else 0,
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/check-address")
def check_address(req: AddressRequest):
    address = req.address.lower().strip()

    code = get_code(address)
    if not code or code == "0x":
        return {"address": address, "error": "Not a contract address"}

    features = build_feature_row(address)
    X = np.array([[features[col] for col in feature_columns]])
    risk_score = float(model.predict_proba(X)[0][1])
    prediction = "scam" if risk_score >= 0.5 else "legit"

    return {
        "address": address,
        "risk_score": round(risk_score, 3),
        "prediction": prediction,
        "flags": features,
    }