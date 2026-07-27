# AQI-Sentinel API Reference

## 1. Overview

AQI-Sentinel exposes a small REST API through a FastAPI backend.

Base URL during local development:

```text
http://localhost:8000
```

All routes return JSON except the favicon endpoint.

The API is intentionally thin. Request validation happens in `main.py`, and the actual work is delegated to the orchestrator and agents.

---

## 2. Common response conventions

### 2.1 Provenance fields
Many outputs include a `source` field with values such as:

- `live`
- `fallback`
- `cache hit`
- `internal`
- `template_fallback`
- `not_configured`

These values tell you whether the result came from a live API, a cached response, a deterministic fallback, or an internal computation step.

### 2.2 Trace entries
Several endpoints return a `trace` list. Each trace item has this shape:

```json
{
  "agent": "DataAgent",
  "action": "fetch_weather",
  "source": "live",
  "detail": "open-meteo forecast API",
  "t": 1712345678.123
}
```

### 2.3 Error handling
The API uses FastAPI `HTTPException` responses for invalid city or zone values.

Common error response:

```json
{
  "detail": "Unknown city 'foo'"
}
```

or

```json
{
  "detail": "Unknown zone 'bar' for city 'delhi'"
}
```

---

## 3. Endpoint summary

| Method | Path | Purpose |
|---|---|---|
| GET | `/favicon.ico` | Returns HTTP 204 |
| GET | `/api/health` | Backend status and LLM mode |
| GET | `/api/cities` | List all cities and zones |
| GET | `/api/city/{city_id}/overview` | City-wide AQI overview |
| GET | `/api/city/{city_id}/zone/{zone}/attribution` | Zone-level source attribution |
| GET | `/api/city/{city_id}/zone/{zone}/forecast` | Zone-level AQI forecast |
| GET | `/api/city/{city_id}/enforcement` | Ranked enforcement priorities |
| GET | `/api/city/{city_id}/zone/{zone}/advisory` | Citizen health advisory |
| GET | `/api/city/{city_id}/validation` | Validation against published studies |
| GET | `/api/city/{city_id}/zone/{zone}/pipeline` | Full pipeline timing run |

---

## 4. Endpoint details

## 4.1 GET `/api/health`

Returns backend status plus the LLM toggle state.

### Response
```json
{
  "status": "ok",
  "llm_enabled": false
}
```

### Notes
- `llm_enabled` becomes `true` when `ANTHROPIC_API_KEY` is configured.

---

## 4.2 GET `/api/cities`

Returns all available cities and their zones.

### Response shape
```json
[
  {
    "id": "delhi",
    "name": "Delhi NCR",
    "lang": "hi",
    "zones": ["Anand Vihar", "RK Puram", "..."]
  }
]
```

### Fields
- `id` — internal city identifier
- `name` — display name
- `lang` — default language code for the city
- `zones` — list of zone names

### Supported city IDs
- `delhi`
- `mumbai`
- `kolkata`
- `bengaluru`
- `chennai`

---

## 4.3 GET `/api/city/{city_id}/overview`

Returns a city-level summary built from all zones.

### Path parameters
- `city_id` — one of the supported city IDs

### Response shape
```json
{
  "city": "Delhi NCR",
  "overall_aqi": 187,
  "zones": [...],
  "trace": [...]
}
```

### Response fields
- `city` — display name
- `overall_aqi` — rounded average AQI across the city’s zones
- `zones` — list of zone-level attribution results
- `trace` — execution trace for the overview run

### Notes
- The city average is computed from the attribution result of each zone.
- Zone processing is parallelised.

---

## 4.4 GET `/api/city/{city_id}/zone/{zone}/attribution`

Returns detailed source attribution for a single zone.

### Path parameters
- `city_id`
- `zone`

### Response shape
```json
{
  "zone": "Anand Vihar",
  "aqi": 211,
  "aqi_source": "live",
  "landuse_source": "live",
  "shares": {
    "Vehicular": 0.31,
    "Construction": 0.16,
    "Industrial": 0.11,
    "Road & Fugitive Dust": 0.18,
    "Biomass / Waste Burning": 0.09,
    "Regional Transport": 0.15
  },
  "confidence": {
    "Vehicular": 0.72,
    "Construction": 0.68,
    "Industrial": 0.66,
    "Road & Fugitive Dust": 0.69,
    "Biomass / Waste Burning": 0.65,
    "Regional Transport": 0.68
  },
  "causal_narrative": "...",
  "wind_direction_deg": 240,
  "wind_compass": "WSW",
  "wind_speed_kmh": 12.4,
  "wind_source": "live",
  "upwind_sources": [],
  "traffic_congestion_pct": 54.2,
  "traffic_source": "live",
  "thermal_anomaly_count": 2,
  "thermal_source": "live",
  "station_reading": {
    "source": "live",
    "station_name": "..."
  },
  "signals": {
    "industrial_sites": 3,
    "construction_sites": 5,
    "major_roads": 4,
    "pm2_5": 122.1,
    "no2": 41.3
  },
  "trace": [...]
}
```

### Important fields
- `shares` — category-level source contributions
- `confidence` — per-category confidence estimates
- `causal_narrative` — readable explanation
- `upwind_sources` — list of real nearby candidate sources
- `signals` — compact summary of the raw indicators

### Notes
- This endpoint uses live data where available.
- If live data is unavailable, the endpoint still returns a structured fallback response.

---

## 4.5 GET `/api/city/{city_id}/zone/{zone}/forecast`

Returns a hyperlocal 72-hour forecast and backtest information.

### Query parameters
- none

### Response shape
```json
{
  "zone": "Anand Vihar",
  "data_source": "live",
  "forecast_source": "Open-Meteo (CAMS-backed)",
  "forward_forecast_72h": [182.1, 185.4, 188.0],
  "history_used_for_backtest": 120,
  "backtest": {
    "model_name": "holt_winters_additive",
    "rmse_model": 14.2,
    "rmse_persistence": 17.8,
    "improvement_pct": 20.2,
    "holdout_actual": [...],
    "holdout_model_pred": [...],
    "holdout_persistence_pred": [...]
  },
  "trace": [...]
}
```

### Response fields
- `zone`
- `data_source` — live or fallback AQI source
- `forecast_source` — human-readable description of forecast source
- `forward_forecast_72h` — list of future AQI values
- `history_used_for_backtest` — number of hourly points used for validation
- `backtest` — RMSE comparison data, or `null` when history is insufficient

### Notes
- If there is not enough history, the backtest may be `null`.
- The forecast endpoint uses Open-Meteo AQ quality data for the forward horizon and the internal time-series model for backtesting.

---

## 4.6 GET `/api/city/{city_id}/enforcement`

Returns all zones ranked by enforcement priority.

### Path parameters
- `city_id`

### Response shape
```json
{
  "ranked_zones": [
    {
      "zone": "Anand Vihar",
      "score": 87,
      "aqi": 211,
      "aqi_source": "live",
      "top_source": "Vehicular",
      "top_source_confidence": 0.72,
      "wind_speed_ms": 3.4,
      "wind_source": "live",
      "stability_class": "C",
      "plume_ug_m3_at_250_500_1000_2000m": [ ... ],
      "industrial_sites": 3,
      "construction_sites": 5,
      "evidence_source": "live",
      "industrial_refs": [ ... ],
      "construction_refs": [ ... ],
      "primary_target": {
        "category": "Construction",
        "name": "...",
        "osm_url": "...",
        "distance_km": 1.9,
        "bearing_deg": 248,
        "compass_from_zone": "WSW",
        "is_upwind_now": true
      },
      "causal_narrative": "..."
    }
  ],
  "trace": [...]
}
```

### Response fields
- `ranked_zones` — sorted by descending score
- `score` — priority score derived from severity, confidence, and exposure proxy
- `primary_target` — the closest currently upwind real source when one is available

### Notes
- The system does not invent a target when one cannot be supported by live data.
- If no upwind source is identified, `primary_target` is `null`.

---

## 4.7 GET `/api/city/{city_id}/zone/{zone}/advisory`

Returns a short citizen advisory for a specific zone.

### Path parameters
- `city_id`
- `zone`

### Query parameters
- `lang` — optional language code, default `en`

### Supported language codes
- `en`
- `hi`
- `mr`
- `bn`
- `kn`
- `ta`

### Response shape
```json
{
  "zone": "Anand Vihar",
  "lang": "hi",
  "aqi": 211,
  "category": "poor",
  "message": "..."
  ,"generated_by": "template_no_key",
  "vulnerability": {
    "schools": 6,
    "hospitals": 2,
    "source": "live"
  },
  "trace": [...]
}
```

### Response fields
- `zone`
- `lang`
- `aqi`
- `category` — AQI category band
- `message` — advisory text
- `generated_by` — `llm`, `template_no_key`, or `template_llm_error`
- `vulnerability` — schools and hospitals near the zone

### Notes
- If Claude is configured, the advisory can be generated by the LLM.
- If not, the template fallback is used.
- The advisory is intentionally short and actionable.

---

## 4.8 GET `/api/city/{city_id}/validation`

Compares the city-level attribution pattern against a published benchmark study.

### Path parameters
- `city_id`

### Response shape
```json
{
  "available": true,
  "study": "Comprehensive Study on Air Pollution and GHGs in Delhi (IIT Kanpur / DPCC)",
  "study_url": "https://...",
  "study_pollutant": "PM2.5",
  "study_note": "...",
  "categories_compared": 3,
  "categories_total": 6,
  "mean_absolute_error_pct_points": 8.7,
  "comparisons": [
    {
      "category": "Vehicular",
      "our_pct": 19.8,
      "published_pct": 20.0,
      "absolute_error": 0.2,
      "status": "compared"
    },
    {
      "category": "Industrial",
      "our_pct": 12.3,
      "published_pct": null,
      "absolute_error": null,
      "status": "no_independent_benchmark"
    }
  ],
  "trace": [...]
}
```

### Response fields
- `available` — whether a benchmark exists for the city
- `study` — title of the published study
- `study_url` — source URL
- `study_pollutant` — pollutant used in the comparison
- `study_note` — benchmark caveat
- `categories_compared` — count of categories with overlap
- `categories_total` — total categories produced by the model
- `mean_absolute_error_pct_points` — MAE over comparable categories
- `comparisons` — per-category comparison rows

### Notes
- If the city has no registered benchmark, the endpoint returns `{"available": false}`.

---

## 4.9 GET `/api/city/{city_id}/zone/{zone}/pipeline`

Runs the full intervention pipeline for a single zone and measures wall-clock latency.

### Path parameters
- `city_id`
- `zone`

### Query parameters
- `lang` — optional language code, default `en`

### Response shape
```json
{
  "zone": "Anand Vihar",
  "pipeline_seconds": 4.832,
  "trace_span_seconds": 4.821,
  "steps": 17,
  "stages": {
    "attribution_aqi": 211,
    "forecast_backtest_available": true,
    "dispersion_stability_class": "C",
    "advisory_generated_by": "template_no_key"
  },
  "trace": [...]
}
```

### Response fields
- `pipeline_seconds` — wall-clock time for the full pipeline
- `trace_span_seconds` — time between the first and last trace entry
- `steps` — number of logged trace events
- `stages` — summary of the major sub-stages
- `trace` — detailed execution log

### Notes
This endpoint is the closest thing in the prototype to a “signal-to-intervention” latency benchmark.

---

## 5. Error responses

### 5.1 Unknown city
```json
{
  "detail": "Unknown city 'abc'"
}
```

### 5.2 Unknown zone
```json
{
  "detail": "Unknown zone 'foo' for city 'delhi'"
}
```

### 5.3 Typical status codes
- `200 OK` — successful request
- `204 No Content` — favicon
- `404 Not Found` — unknown city or zone
- `500 Internal Server Error` — unexpected application failure

---

## 6. CORS behaviour

The backend currently allows all origins, methods, and headers for hackathon/demo use.

That is defined in `main.py` and is intended for local development and submission-time testing.

---

## 7. Suggested integration order

If you are consuming the API from the frontend or another client, the recommended request sequence is:

1. `GET /api/health`
2. `GET /api/cities`
3. `GET /api/city/{city_id}/overview`
4. `GET /api/city/{city_id}/zone/{zone}/attribution`
5. `GET /api/city/{city_id}/zone/{zone}/forecast`
6. `GET /api/city/{city_id}/enforcement`
7. `GET /api/city/{city_id}/zone/{zone}/advisory`
8. `GET /api/city/{city_id}/validation`
9. `GET /api/city/{city_id}/zone/{zone}/pipeline`

This order mirrors how the dashboard typically reveals the system.

---

## 8. Summary

AQI-Sentinel’s API is intentionally compact but expressive.

It provides everything the frontend needs for:

- city overview
- explainable attribution
- forecasting
- enforcement ranking
- citizen advisories
- validation
- response-time benchmarking

The contract is simple: each endpoint returns structured JSON with clear provenance and traceability.
