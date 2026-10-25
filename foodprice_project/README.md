---
title: Food Price Spike Sri Lanka
emoji: 🍅
colorFrom: green
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
---

# Early Warning of Food Price Spikes in Sri Lankan Markets

**Live demo (Azure):** https://foodprice-spike-1340.azurewebsites.net

**Question:** will the retail price of a food item in a Sri Lankan market rise by 10% or more next month? (classification)
**Data:** real retail food prices from the UN World Food Programme (WFP), 44 markets, 42 items, 2004 to September 2025.
**Models:** Random Forest, XGBoost, LightGBM, CatBoost (best chosen on validation ROC-AUC), explained with SHAP.
**App:** FastAPI backend + Streamlit dashboard with a per-prediction SHAP explanation.

## Folder structure
```
data/        wfp_food_prices_lka.csv (WFP data), spike_dataset.csv (engineered table, created by the notebook)
notebooks/   food_price_spike_shap.ipynb (EDA, features, 4 models, selection, SHAP, inference demo; already executed)
models/      best_model.joblib + feature list, markets, items, example, meta.json (created by the notebook)
backend/     api.py (FastAPI), predictor.py (features + prediction + SHAP), explain.py (SHAP helper)
frontend/    app.py (Streamlit dashboard)
outputs/     charts, metrics.csv, dashboard screenshots
report/      Food_Price_Spike_Report.docx (+ PDF)
```

## How to run (Windows)
Use a folder that is NOT inside OneDrive, for example `C:\food_project`.
1. Install Python 3.10 to 3.13 (newest 3.14 may lack some packages). Tick "Add Python to PATH".
2. Open a terminal in this folder (the one containing `requirements.txt`) and run:
   ```
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```
   (`requirements.txt` is all you need to run the app. To re-run the notebook as well, also run `pip install -r requirements-notebook.txt`.)
3. (Optional) re-run the experiment: `jupyter notebook`, open `notebooks/food_price_spike_shap.ipynb`, Kernel > Restart & Run All (about 5 to 10 minutes).
4. Terminal 1, backend: `uvicorn backend.api:app --port 8000` (docs at http://127.0.0.1:8000/docs)
5. Terminal 2 (run `venv\Scripts\activate` first), dashboard: `python -m streamlit run frontend/app.py`
   It opens at http://localhost:8501. Click "Load the held-out example", then "Check spike risk".

If the backend is not running, the dashboard loads the model directly and says so under the result.

## Data source
WFP food prices for Sri Lanka, Humanitarian Data Exchange: https://data.humdata.org/dataset/wfp-food-prices-for-sri-lanka

## Put the app online (deployment)
The app is one Docker container that runs the FastAPI backend (internal) and the Streamlit dashboard (public) together, so the public site still uses the backend.
Files for this: `Dockerfile`, `start.sh`, `render.yaml`, `requirements.txt`, `.streamlit/config.toml`.
You need a free account on the service you choose. Pick ONE option.

**Option A: Hugging Face Spaces (easiest, free, no card)**
1. Sign in at https://huggingface.co, click New > Space, choose SDK **Docker** (blank template), visibility Public.
2. In the Space, click Files > Add file > Upload files, and upload the whole project folder contents (the `Dockerfile` must be at the top level). Keep the `README.md` that the Space created, or add this at the very top of it:
   ```
   ---
   title: Sri Lanka Food Price Early Warning
   sdk: docker
   app_port: 7860
   ---
   ```
3. Wait for the build (a few minutes). Your public link is shown at the top of the Space.

**Option B: Render (free tier sleeps after inactivity)**
1. Put the project in a GitHub repository (GitHub website > New repository > upload files).
2. At https://render.com choose New > Blueprint, connect that repository, and deploy. `render.yaml` does the rest.

**Option C: Streamlit Community Cloud (dashboard only)**
1. Put the project in a public GitHub repository.
2. At https://share.streamlit.io choose New app, pick the repository, set the main file to `frontend/app.py`, and under Advanced settings choose Python 3.11 or 3.12.
3. This runs only the dashboard. It loads the model directly (it says "local model (backend not running)" under each result), so the FastAPI backend is not part of this option.

Test the container locally with Docker Desktop: `docker build -t foodprice .` then `docker run -p 7860:7860 foodprice` and open http://localhost:7860


## Azure
See `AZURE_DEPLOY.md` (one-script deployment with `azure_deploy.ps1` to Azure App Service for Containers).
