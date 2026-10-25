#!/bin/sh
# Starts the FastAPI backend (internal, port 8000) and the Streamlit dashboard (public, $PORT or 8501).
export API_URL="http://127.0.0.1:8001"
# Uses "python -m" so it also works inside Azure's Python environment.
python -m uvicorn backend.api:app --host 127.0.0.1 --port 8001 &
exec python -m streamlit run frontend/app.py --server.port "${PORT:-8501}" --server.address 0.0.0.0 --server.headless true --server.enableCORS false --server.enableXsrfProtection false
