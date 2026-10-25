"""Loads the trained model and turns raw user inputs into a spike prediction with a SHAP explanation.
Used by the FastAPI backend (api.py) and, as a fallback, by the Streamlit dashboard."""
import json
import math
import re
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from backend.explain import SpikeExplainer

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

_model = joblib.load(MODELS_DIR / "best_model.joblib")
FEATURES = json.load(open(MODELS_DIR / "feature_columns.json"))
MARKETS = json.load(open(MODELS_DIR / "markets.json"))
COMMODITIES = json.load(open(MODELS_DIR / "commodities.json"))      # display name -> model column
META = json.load(open(MODELS_DIR / "meta.json"))
_explainer = SpikeExplainer(_model)
_clean = lambda x: re.sub(r"[^0-9A-Za-z]+", "_", x).strip("_")
COMMODITY_COLS = set(COMMODITIES.values())
PROVINCE_COLS = [f for f in FEATURES if f.startswith("province_")]


def build_features(commodity, market, month, price_now, price_prev, price_3m, national_avg_now, national_avg_prev):
    if commodity not in COMMODITIES:
        raise ValueError(f"Unknown item: {commodity}")
    if market not in MARKETS:
        raise ValueError(f"Unknown market: {market}")
    if min(price_now, price_prev, price_3m, national_avg_now, national_avg_prev) <= 0:
        raise ValueError("All prices must be greater than zero")
    m = MARKETS[market]
    row = {f: 0.0 for f in FEATURES}
    row.update({
        "price_now": price_now,
        "change_1m": math.log(price_now / price_prev),
        "change_2m": math.log(price_prev / price_3m),
        "vs_3m_avg": math.log(price_now / ((price_now + price_prev + price_3m) / 3)),
        "national_avg_now": national_avg_now,
        "national_change_1m": math.log(national_avg_now / national_avg_prev),
        "market_vs_national": math.log(price_now / national_avg_now),
        "month": month, "latitude": m["latitude"], "longitude": m["longitude"],
    })
    row[COMMODITIES[commodity]] = 1.0
    prov_col = "province_" + _clean(m["province"])
    if prov_col in row:
        row[prov_col] = 1.0
    return pd.DataFrame([row])[FEATURES]


def predict_spike(commodity, market, month, price_now, price_prev, price_3m, national_avg_now, national_avg_prev):
    X = build_features(commodity, market, month, price_now, price_prev, price_3m, national_avg_now, national_avg_prev)
    prob = float(_model.predict_proba(X)[0, 1])
    sv = _explainer.explain(X)[0]
    contrib = pd.Series(sv, index=FEATURES)
    grouped = {
        "Item": float(contrib[[c for c in FEATURES if c in COMMODITY_COLS]].sum()),
        "Province": float(contrib[PROVINCE_COLS].sum()),
    }
    labels = {
        "price_now": "Latest price", "change_1m": "Price change last month", "change_2m": "Price change month before",
        "vs_3m_avg": "Latest price vs 3-month average", "national_avg_now": "National average price",
        "national_change_1m": "National price change last month", "market_vs_national": "Market vs national price",
        "month": "Calendar month", "latitude": "Market latitude", "longitude": "Market longitude",
    }
    for f, lab in labels.items():
        grouped[lab] = float(contrib[f])
    values = {"Item": commodity, "Province": MARKETS[market]["province"], "Latest price": f"{price_now:,.2f} LKR",
              "Price change last month": f"{(price_now / price_prev - 1):+.1%}", "Price change month before": f"{(price_prev / price_3m - 1):+.1%}",
              "Latest price vs 3-month average": f"{(price_now / ((price_now + price_prev + price_3m) / 3) - 1):+.1%}",
              "National average price": f"{national_avg_now:,.2f} LKR",
              "National price change last month": f"{(national_avg_now / national_avg_prev - 1):+.1%}",
              "Market vs national price": f"{(price_now / national_avg_now - 1):+.1%}", "Calendar month": str(month)}
    explanation = sorted(({"feature": k, "value": values.get(k, ""), "shap": round(v, 4)} for k, v in grouped.items()),
                         key=lambda e: abs(e["shap"]), reverse=True)
    return {"spike_probability": round(prob, 4), "alert": bool(prob >= META["threshold"]), "threshold": META["threshold"],
            "spike_price_at_least": round(price_now * 1.10, 2), "model": META["model"], "shap_unit": META["shap_unit"],
            "explanation": explanation[:8]}
