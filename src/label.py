import pandas as pd
from pathlib import Path

RAW_DIR = Path("data/raw")
OUT_DIR = Path("data/labeled")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_scam_tokens():
    path = RAW_DIR / "scam_tokens_live.csv"
    if not path.exists():
        print("scam_tokens_live.csv not found — run fetch.py first")
        return pd.DataFrame()

    df = pd.read_csv(path, low_memory=False)
    df["address"] = df["address"].str.lower().str.strip()
    df["label"] = 1
    return df


def load_legit_tokens(scam_addresses):
    df = pd.read_csv(RAW_DIR / "token_dataset_bsc.csv", low_memory=False)
    df["address"] = df["address"].str.lower().str.strip()
    df = df[~df["address"].isin(scam_addresses)]
    df["label"] = 0
    return df


def attach_liquidity(df):
    lp_path = RAW_DIR / "lp_dataset_bsc.csv"
    if not lp_path.exists():
        print("lp_dataset_bsc.csv not found — skipping liquidity attachment for now")
        df["has_liquidity_pool"] = None
        return df

    lp_df = pd.read_csv(lp_path, low_memory=False)
    lp_df["token0"] = lp_df["token0"].str.lower().str.strip()
    lp_df["token1"] = lp_df["token1"].str.lower().str.strip()

    lp_addresses = set(lp_df["token0"]) | set(lp_df["token1"])
    df["has_liquidity_pool"] = df["address"].isin(lp_addresses)
    return df


def main():
    scam_df = load_scam_tokens()
    scam_addresses = set(scam_df["address"]) if not scam_df.empty else set()

    legit_df = load_legit_tokens(scam_addresses)

    combined = pd.concat([scam_df, legit_df], ignore_index=True)
    combined = attach_liquidity(combined)

    scam_count = int((combined["label"] == 1).sum())
    legit_count = int((combined["label"] == 0).sum())
    print(f"Labeled {len(combined)} tokens — {scam_count} scam, {legit_count} legit")

    out_path = OUT_DIR / "labeled_tokens.csv"
    combined.to_csv(out_path, index=False)
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()