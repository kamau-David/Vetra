# Vetra

Vetra flags DeFi rug-pulls and scam tokens in real time by analyzing on-chain wallet and contract behavior before the collapse happens.

Built for **GIBC V2 — Track 02 (Applied: Medical Technology & Finance)**.

## The Problem

DeFi rug-pulls cost investors over a billion dollars a year. A token can look legitimate — website, community, rising price — and then have its liquidity drained in minutes, with zero recourse for the people who bought in. Manual audits are too slow and too expensive to catch this before it happens. There is no free, real-time, automated early-warning system watching for the behavioral fingerprints of a scam before it collapses.

## What Vetra Does

Vetra pulls live transaction and contract data for a given token and calculates a risk score based on known rug-pull signatures:

- **Liquidity concentration** — how much of the pool a single wallet could drain instantly
- **Wallet age and history** — newly created "developer" wallets with no prior activity
- **Contract code similarity** — matches against templates seen in confirmed past scams
- **Ownership permissions** — active minting or trading-disable functions still held by the owner
- **Sell-order spikes** — sudden large sells from wallets with no prior selling activity

Paste a contract address, get a risk score and a breakdown of exactly which signals triggered it.

## Why It's Different

Most fraud-detection projects assume a banking system, currency, or regulatory framework tied to one country. On-chain data has none of that — a rug-pull looks the same everywhere. Vetra targets BNB Smart Chain, where scam-token volume is highest, using free, publicly available transaction data with no assumptions baked in about who or where the victim is.

## Tech Stack

- **Data source:** BscScan API
- **Backend / data processing:** Python, pandas, web3.py, python-dotenv
- **Model:** scikit-learn (classifier), SHAP for explainability
- **API layer:** FastAPI
- **Dashboard:** Streamlit
- **Storage:** SQLite

## How It Works

1. Pull historical transaction and contract data for labeled scam tokens and legitimate tokens via the BscScan API
2. Engineer features from the raw data (liquidity concentration, wallet age, permissions, sell patterns, code similarity)
3. Train a classifier to distinguish scam patterns from legitimate ones
4. Serve the model through a FastAPI endpoint
5. Display results in a Streamlit dashboard with a full breakdown of flagged signals

## Setup

```bash
git clone https://github.com/kamau-David/vetra.git
cd vetra
pip install -r requirements.txt
```

Add your BscScan API key:

```bash
cp .env.example .env
```

Open `.env` and replace the placeholder with your actual key from [bscscan.com/myapikey](https://bscscan.com/myapikey). `.env` is gitignored — never commit it.

Run the backend:

```bash
uvicorn app.main:app --reload
```

Run the dashboard:

```bash
streamlit run dashboard/app.py
```

## Demo

A recorded walkthrough replays a real, confirmed past rug-pull through the model, showing the risk score rising in the hours before the token's actual collapse.



## Team

- Davian (David Kamau) — [GitHub](https://github.com/kamau-David)

## License

MIT
