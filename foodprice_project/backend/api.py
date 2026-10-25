"""FastAPI backend: the machine learning model runs here.
Start with:  uvicorn backend.api:app --port 8000   (run from the project folder)
Interactive docs: http://127.0.0.1:8000/docs"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from backend import predictor

app = FastAPI(title="Sri Lanka Food Price Spike Early Warning", version="1.0")


class PredictRequest(BaseModel):
    commodity: str = Field(..., examples=["Tomatoes"])
    market: str = Field(..., examples=["Colombo City"])
    month: int = Field(..., ge=1, le=12, description="Calendar month you are predicting (1-12)")
    price_now: float = Field(..., gt=0, description="Price (LKR) in the latest known month")
    price_prev: float = Field(..., gt=0, description="Price (LKR) one month before that")
    price_3m: float = Field(..., gt=0, description="Price (LKR) two months before that")
    national_avg_now: float = Field(..., gt=0, description="National average price of this item in the latest known month")
    national_avg_prev: float = Field(..., gt=0, description="National average price of this item one month earlier")


@app.get("/health")
def health():
    return {"status": "ok", "model": predictor.META["model"]}


@app.get("/model-info")
def model_info():
    return predictor.META


@app.get("/markets")
def markets():
    return predictor.MARKETS


@app.get("/commodities")
def commodities():
    return sorted(predictor.COMMODITIES)


@app.post("/predict")
def predict(req: PredictRequest):
    try:
        return predictor.predict_spike(**req.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
