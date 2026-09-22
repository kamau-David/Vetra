import requests
import streamlit as st

API_URL = "http://localhost:8000/check-address"

st.set_page_config(page_title="Vetra", page_icon="🛡️")
st.title("🛡️ Vetra")
st.caption("Real-time DeFi rug-pull and scam token detection on BNB Smart Chain")

address = st.text_input("Token contract address", placeholder="0x...")
check = st.button("Check token")

if check and address:
    with st.spinner("Analyzing on-chain data..."):
        try:
            resp = requests.post(API_URL, json={"address": address}, timeout=30)
            data = resp.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Could not reach the backend: {e}")
            data = None

    if data:
        if "error" in data:
            st.warning(data["error"])
        else:
            score = data["risk_score"]
            prediction = data["prediction"]

            if prediction == "scam":
                st.error(f"⚠️ HIGH RISK — {score * 100:.1f}% risk score")
            else:
                st.success(f"✅ LOW RISK — {score * 100:.1f}% risk score")

            st.subheader("Signal breakdown")
            flags = data["flags"]

            col1, col2, col3 = st.columns(3)
            col1.metric("Supply magnitude", flags["supply_log"])
            col2.metric("Has liquidity pool", "Yes" if flags["has_liquidity_pool_live"] else "No")
            col3.metric("Owner not renounced", "Yes" if flags["owner_not_renounced"] else "No")

            st.caption(f"Address checked: {data['address']}")
elif check:
    st.warning("Enter a contract address first")