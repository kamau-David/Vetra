import pandas as pd
from pathlib import Path

RAW_DIR = Path("data/raw")
OUT_DIR = Path("data/labeled")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_scam_addresses():
    df = pd.read_csv(RAW_DIR / "rugpull_dataset.csv")
    df = df[df["Chain"].str.upper() == "BSC"]
    return set(df["Address"].str.lower().str.strip())


def load_tokens():
    df = pd.read_csv(RAW_DIR / "token_dataset_bsc.csv")
    df["address"] = df["address"].str.lower().str.strip()
    return df


def label_tokens(tokens_df, scam_addresses):
    tokens_df["label"] = tokens_df["address"].apply(
        lambda a: 1 if a in scam_addresses else 0
    )
    return tokens_df


def attach_liquidity(tokens_df):
    lp_df = pd.read_csv(RAW_DIR / "lp_dataset_bsc.csv")
    lp_df["token0"] = lp_df["token0"].str.lower().str.strip()
    lp_df["token1"] = lp_df["token1"].str.lower().str.strip()

    lp_map = {}
    for _, row in lp_df.iterrows():
        lp_map.setdefault(row["token0"], []).append(row["liquidity_token"])
        lp_map.setdefault(row["token1"], []).append(row["liquidity_token"])

    tokens_df["has_liquidity_pool"] = tokens_df["address"].apply(
        lambda a: a in lp_map
    )
    return tokens_df


def main():
    scam_addresses = load_scam_addresses()
    tokens_df = load_tokens()
    tokens_df = label_tokens(tokens_df, scam_addresses)
    tokens_df = attach_liquidity(tokens_df)

    scam_count = tokens_df["label"].sum()
    total = len(tokens_df)
    print(f"Labeled {total} tokens — {scam_count} scam, {total - scam_count} legit")

    out_path = OUT_DIR / "labeled_tokens.csv"
    tokens_df.to_csv(out_path, index=False)
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()