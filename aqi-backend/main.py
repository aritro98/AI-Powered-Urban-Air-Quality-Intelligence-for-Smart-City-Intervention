"""
AQI-Sentinel backend — FastAPI app.

Run with:
    uvicorn main:app --reload --port 8000

Then open frontend/index.html (or serve it separately) and point it at
http://localhost:8000.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

import cities
import config
from agents.orchestrator import Orchestrator

app = FastAPI(title="AQI-Sentinel API", version="0.4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # local dev / hackathon demo only
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = Orchestrator()


@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)


def _validate_city(city_id):
    if city_id not in cities.CITIES:
        raise HTTPException(status_code=404, detail=f"Unknown city '{city_id}'")


def _validate_zone(city_id, zone):
    if zone not in cities.CITIES[city_id]["zones"]:
        raise HTTPException(status_code=404, detail=f"Unknown zone '{zone}' for city '{city_id}'")


@app.get("/api/health")
def health():
    return {"status": "ok", "llm_enabled": config.USE_LLM}


@app.get("/api/cities")
def list_cities():
    return [
        {"id": cid, "name": c["name"], "lang": c["lang"], "zones": list(c["zones"].keys())}
        for cid, c in cities.CITIES.items()
    ]


@app.get("/api/city/{city_id}/overview")
def city_overview(city_id: str):
    _validate_city(city_id)
    return orchestrator.city_overview(city_id)


@app.get("/api/city/{city_id}/zone/{zone}/attribution")
def zone_attribution(city_id: str, zone: str):
    _validate_city(city_id)
    _validate_zone(city_id, zone)
    return orchestrator.zone_attribution(city_id, zone)


@app.get("/api/city/{city_id}/zone/{zone}/forecast")
def zone_forecast(city_id: str, zone: str):
    _validate_city(city_id)
    _validate_zone(city_id, zone)
    return orchestrator.zone_forecast(city_id, zone)


@app.get("/api/city/{city_id}/enforcement")
def enforcement(city_id: str):
    _validate_city(city_id)
    return orchestrator.enforcement(city_id)


@app.get("/api/city/{city_id}/zone/{zone}/advisory")
def advisory(city_id: str, zone: str, lang: str = "en"):
    _validate_city(city_id)
    _validate_zone(city_id, zone)
    return orchestrator.advisory(city_id, zone, lang)


@app.get("/api/city/{city_id}/validation")
def validation(city_id: str):
    _validate_city(city_id)
    return orchestrator.validation(city_id)


@app.get("/api/city/{city_id}/zone/{zone}/pipeline")
def full_pipeline(city_id: str, zone: str, lang: str = "en"):
    _validate_city(city_id)
    _validate_zone(city_id, zone)
    return orchestrator.full_pipeline(city_id, zone, lang)