"""FastAPI microservice exposure for the InsightAgent engine."""
from __future__ import annotations

from fastapi import Body, FastAPI

from .engine import InsightEngine
from .schemas import InsightRequest


app = FastAPI(title="InsightAgent Engine", version="0.1.0")
engine = InsightEngine()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "InsightAgent Engine is ready. POST /insights with marketing data."}


@app.post("/insights")
def generate_insights(payload: dict = Body(...)) -> dict:
    request = InsightRequest.model_validate(payload)
    response = engine.run(request)
    return response.to_json()
