"""Streamlit dashboard. Run from the project folder:  streamlit run frontend/app.py
It calls the FastAPI backend (default http://127.0.0.1:8000). If the backend is not running,
it falls back to loading the model directly so the dashboard still works."""
import json
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import requests
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Sri Lanka Food Price Early Warning", page_icon="🛒", layout="wide")


def call_prediction(payload: dict):
    """Try the FastAPI backend first; fall back to the local model."""
    try:
        r = requests.post(f"{API_URL}/predict", json=payload, timeout=10)
        r.raise_for_status()
        return r.json(), f"FastAPI backend ({API_URL})"
    except Exception:
        from backend import predictor
        return predictor.predict_spike(**payload), "local model (backend not running)"


@st.cache_data
def load_prices():
    d = pd.read_csv(ROOT / "data" / "wfp_food_prices_lka.csv", parse_dates=["date"])
    return d[(d.market != "National Average") & (d.pricetype == "Retail")]


meta = json.load(open(ROOT / "models" / "meta.json"))
markets = json.load(open(ROOT / "models" / "markets.json"))
items = sorted(json.load(open(ROOT / "models" / "commodities.json")))
example = json.load(open(ROOT / "models" / "holdout_example.json"))
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

st.title("🛒 Sri Lanka Food Price Spike Early Warning")
st.caption(f"Will a food item's price rise by 10% or more next month? Model: **{meta['model']}** "
           f"(test ROC-AUC {meta['test_AUC']}, precision {meta['test_precision']}, recall {meta['test_recall']}). "
           f"Based on WFP market prices up to {meta['trained_on'].replace('prices up to ', '')}.")

for _k, _v in dict(item="Tomatoes", market="Colombo City", month="September", n1=200.0, n2=200.0, p1=200.0, p2=200.0, p3=200.0,
                   ex_item="Tomatoes", ex_mk=["Colombo City", "Kandy", "Jaffna"]).items():
    st.session_state.setdefault(_k, _v)

tab_pred, tab_models, tab_shap, tab_data = st.tabs(["Predict", "Model comparison", "SHAP insights", "Price explorer"])

with tab_pred:
    if st.button("Load the held-out example (Tomatoes, Colombo City, September)"):
        st.session_state.update(item=example["commodity"], market=example["market"], month=MONTHS[example["month"] - 1],
                                p1=example["price_now"], p2=example["price_prev"], p3=example["price_3m"],
                                n1=example["national_avg_now"], n2=example["national_avg_prev"])
    c1, c2 = st.columns(2)
    with c1:
        item = st.selectbox("Food item", items, key="item")
        market = st.selectbox("Market", sorted(markets), key="market")
        month = st.selectbox("Month you want to predict", MONTHS, key="month")
        n1 = st.number_input("National average price of this item, 1 month before (LKR)", 0.01, 100000.0, key="n1")
        n2 = st.number_input("National average price of this item, 2 months before (LKR)", 0.01, 100000.0, key="n2")
    with c2:
        p1 = st.number_input("Price in this market, 1 month before (latest known, LKR)", 0.01, 100000.0, key="p1")
        p2 = st.number_input("Price in this market, 2 months before (LKR)", 0.01, 100000.0, key="p2")
        p3 = st.number_input("Price in this market, 3 months before (LKR)", 0.01, 100000.0, key="p3")

    if st.button("Check spike risk", type="primary"):
        payload = dict(commodity=item, market=market, month=MONTHS.index(month) + 1, price_now=p1, price_prev=p2, price_3m=p3,
                       national_avg_now=n1, national_avg_prev=n2)
        res, source = call_prediction(payload)
        m1, m2, m3 = st.columns(3)
        m1.metric("Spike probability", f"{res['spike_probability']:.0%}")
        m2.metric("Alert", "⚠️ SPIKE ALERT" if res["alert"] else "✅ No alert")
        m3.metric("A spike would mean a price of at least", f"{res['spike_price_at_least']:,.0f} LKR")
        st.caption(f"Alert threshold {res['threshold']:.2f}. Typically about {meta['spike_rate_test']:.0%} of item-months are spikes, so a probability above that means higher-than-usual risk. "
                   f"Served by: {source}")
        st.subheader("Why? (SHAP explanation)")
        unit = "log-odds" if res["shap_unit"] == "log-odds" else "probability"
        ex = pd.DataFrame(res["explanation"])
        ex["label"] = ex["feature"] + " (" + ex["value"] + ")"
        ex = ex.iloc[::-1]
        fig, ax = plt.subplots(figsize=(8.5, 3.8))
        ax.barh(ex["label"], ex["shap"], color=["#eb6834" if v > 0 else "#2a78d6" for v in ex["shap"]], height=0.65)
        ax.axvline(0, color="#898781", linewidth=1)
        ax.set_xlabel("Push on spike risk (SHAP value)"); ax.grid(axis="y", visible=False)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        fig.tight_layout()
        st.pyplot(fig)
        st.caption(f"Orange bars push the spike risk **up**, blue bars push it **down** (SHAP values in {unit}).")
        if (item, market) == (example["commodity"], example["market"]) and MONTHS.index(month) + 1 == example["month"]:
            st.info(f"For comparison: the actual price rose from {example['price_now']:,.2f} to {example['actual_next_price']:,.2f} LKR "
                    f"({example['actual_next_price'] / example['price_now'] - 1:+.1%}), so there was {'a' if example['actual_spike'] else 'no'} spike.")

with tab_models:
    st.subheader("Four models compared (ranked by validation ROC-AUC)")
    st.caption("Validation (Jul-Dec 2024) was used to choose the best model. Test (Jan-Sep 2025) is the final honest score.")
    metrics = pd.read_csv(ROOT / "outputs" / "metrics.csv").set_index("Model")
    st.dataframe(metrics[["Val_AUC", "Test_AUC", "Test_PR_AUC", "Test_Precision", "Test_Recall", "Test_F1", "Train_seconds"]], use_container_width=True)
    st.image(str(ROOT / "outputs" / "model_comparison.png"))
    st.image(str(ROOT / "outputs" / "roc_pr_curves.png"))

with tab_shap:
    st.subheader("What drives the spike predictions?")
    st.image(str(ROOT / "outputs" / "shap_importance.png"))
    st.image(str(ROOT / "outputs" / "shap_beeswarm.png"))
    st.image(str(ROOT / "outputs" / "shap_items.png"))
    st.image(str(ROOT / "outputs" / "shap_dependence.png"))

with tab_data:
    st.subheader("Price history")
    prices = load_prices()
    a, b = st.columns(2)
    it = a.selectbox("Item", sorted(prices.commodity.unique()), key="ex_item")
    mk = b.multiselect("Markets", sorted(prices.market.unique()), key="ex_mk")
    sub = prices[(prices.commodity == it) & (prices.market.isin(mk)) & (prices.date >= "2023-06-01")]
    if len(sub):
        st.line_chart(sub.pivot_table(index="date", columns="market", values="price"))
        st.caption("Retail price in LKR (WFP data, June 2023 onwards).")

st.divider()
st.caption("Data: World Food Programme (WFP) retail food prices for Sri Lanka, via the Humanitarian Data Exchange "
           "(licence: Creative Commons Attribution for Intergovernmental Organisations, CC BY-IGO). "
           "This is a student project; predictions are estimates and not official forecasts.")
