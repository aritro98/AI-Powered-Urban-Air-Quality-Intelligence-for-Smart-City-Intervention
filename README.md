# AQI-Sentinel: AI-Powered Urban Air Quality Intelligence for Smart City Intervention

> *From "the air is dirty, here are the numbers" → "the air will be dangerous tomorrow in this area because of these sources — here is where to send enforcement teams today."*

**Theme:** Smart Cities / Environmental Intelligence / Geospatial Analytics / Public Health

## Overview
AQI-Sentinel is a 6-agent AI platform that fuses real monitoring station data, satellite imagery, mobility feeds, meteorological forecasts, and geospatial land-use layers to answer these questions city administrators actually need:
| Question | Agent | How |
|----|----|----|
| **Why is the air bad here, right now?** | Attribution Agent | Real wind bearing + real OSM land-use → names a specific upwind source, not a category percentage |
| **How bad will it be in 24-72 hours?** | Forecast Agent | Holt-Winters model on real historical AQI, honestly backtested against a persistence baseline |
| **Where should officials go right now?** | Enforcement Agent | Severity × confidence × exposure ranking + real Gaussian-plume dispersion + real upwind target |
| **What should citizens be advised to do now?** | Citizen Advisory Agent | Current AQI + vulnerability layer + language-aware guidance → generates short, actionable health advice for residents and sensitive groups |
| **How reliable is the output, and how fast was it generated?** | Validation + Response Time Agents | Published-study comparison + honest MAE + end-to-end wall-clock timing → shows confidence, benchmark coverage, and signal-to-intervention latency |

**The data exists. The intelligence layer to act on it does not.**

## Problem Context
India's air quality crisis is not a Delhi problem — it is a national urban crisis. In 2024-25, Delhi averaged an AQI of 218 (classified 'Poor' or worse for over 200 days), but the situation across other metros is nearly as severe: Mumbai recorded dangerous AQI levels on over 60 days in 2024, Kolkata averaged AQI above 150 for large parts of the winter season, and Bengaluru and Chennai — long considered relatively clean cities — have seen measurable deterioration as vehicle density and construction activity surge. CPCB's National Air Quality data for 2024 shows that 24 of India's 50 most polluted cities are Tier 1 or Tier 2 urban centres. The Lancet Planetary Health journal estimated 1.67 million premature deaths annually from air pollution in India — a public health burden that falls disproportionately on urban populations. Despite India deploying over 900 Continuous Ambient Air Quality Monitoring Stations (CAAQMS) under the National Clean Air Programme, a 2024 CAG audit found that only 31% of cities with monitoring data had any actionable multi-agency response protocols linked to those readings. The data exists. The intelligence layer to act on it does not.  City administrations need more than dashboards. They need geospatial attribution (which sources are responsible at this location, right now), predictive forecasting (what will AQI be in 24 hours at ward level), and enforcement intelligence (where to deploy inspectors for maximum impact). That combination does not exist today.

## Challenge Statement
Build an AI-powered Urban Air Quality Intelligence platform that fuses monitoring station data, satellite imagery, mobility feeds, meteorological forecasts, and geospatial land use layers to move from reactive monitoring to proactive, evidence-based intervention — giving city administrators the tools to reduce pollution at source rather than just measure it.

In simple words:

India has over 900 Continuous Ambient Air Quality Monitoring Stations (CAAQMS) deployed under the National Clean Air Programme. A 2024 CAG audit found that only 31% of cities with monitoring data had any actionable multi-agency response protocol linked to those readings. City officials look at these numbers and say "the air is bad today" — but they cannot do much about it because they do not know exactly why it is bad, where it is coming from, or how bad it will be tomorrow. This challenge asks you to build a platform that:

Takes data from multiple sources simultaneously:
Air quality sensors — what is the AQI right now at each station
Satellite images — where are the pollution clouds, fires, construction sites
Traffic feeds — where are vehicles congested and emitting fumes
Weather forecasts — wind direction, temperature, humidity affecting how pollution spreads
Maps — where are factories, construction zones, waste burning areas located

Uses AI to connect all of this and answer the questions city officials actually need:
- Why is the air bad here right now?
Not just "AQI is 250" but "the AQI is 250 in this ward because there is a construction site 2km upwind and the wind is blowing southeast today"
- How bad will it be tomorrow?
Predict AQI 24-72 hours ahead at neighbourhood level so officials can warn people and schedule interventions before the problem peaks
- Where should officials go right now to fix it fastest?
Instead of randomly sending inspectors — tell them "go to these three specific locations today because they are the largest contributing sources to the current pollution hotspot"

That is what "reactive monitoring to proactive evidence-based intervention" means. You stop reacting to pollution after it happens and start preventing it before it peaks.

## Architecture
Refer to the [diagram](./diagram/) directory to view the full architecture.

**Supporting modules:** `geo_utils.py`, `models/dispersion.py`, `models/timeseries.py`, `reference_data.py`

**Reliability:** `cache.py` (30-min TTL), `circuit_breaker.py` (opens after 2 failures, 120s cooldown)

## Tech Stack
| Layer | Technology |
|---|---|
| Backend | Python 3.13, FastAPI, Uvicorn |
| Agent framework | Custom multi-agent architecture (6 agents + orchestrator) |
| Forecasting | Holt-Winters additive model (hand-implemented, no ML deps) |
| Atmospheric modelling | Gaussian plume (Pasquill-Gifford, Briggs rural coefficients) |
| Geospatial math | Haversine distance, compass bearing, upwind detection |
| Frontend | Vanilla JS, Chart.js, single-file HTML |
| External APIs | Open-Meteo, OSM Overpass, NASA FIRMS, TomTom, OpenAQ |
| LLM hook | Anthropic Claude API (activates when key is configured) |

## Cities & Zones
5 cities, 10 real coordinate zones each:
| City | Language | Zones |
|---|---|---|
| Delhi NCR | Hindi | Anand Vihar, RK Puram, Punjabi Bagh, Dwarka, Rohini, Okhla, ITO, Mundka, Wazirpur, Narela |
| Mumbai | Marathi | Andheri East, Bandra, Worli, Chembur, Borivali, Powai, Dadar, Kurla, Malad, Colaba |
| Kolkata | Bengali | Salt Lake, Howrah, Ballygunge, Behala, Jadavpur, Park Street, Rajarhat, Garia, Tollygunge,Dum Dum |
| Bengaluru | Kannada | Whitefield, Indiranagar, Koramangala, Jayanagar, Electronic City, Yeshwanthpur, Hebbal, Malleshwaram, HSR Layout, Peenya |
| Chennai | Tamil | Adyar, T Nagar, Anna Nagar, Velachery, Guindy, Perambur, Tambaram, Mylapore, Porur, Ambattur |

## Quick Start
### Prerequisites
- Python 3.10+
- Internet connection (live API calls on every request)

### 1. Clone / Set up the project
```bash
cd aqi-backend
pip install -r requirements.txt
```
### 2. Configure API keys (optional but recommended)
```bash
cp .env
# Edit .env and fill in your keys:
```
| Key | Where to get it | Without it |
|---|---|---|
| `NASA_FIRMS_MAP_KEY` | https://firms.modaps.eosdis.nasa.gov/api/map_key/ | Thermal anomaly count falls back to seeded estimate |
| `TOMTOM_API_KEY` | https://developer.tomtom.com/ (free tier, 2,500 calls/day) | Traffic congestion falls back to seeded estimate |
| `OPENAQ_API_KEY` | https://explore.openaq.org/register | Station reading falls back |
| `ANTHROPIC_API_KEY` | https://console.anthropic.com/ | Advisories use hand-written templates instead of Claude |

> **The app runs fully without the ANTHROPIC_API_KEY.** Every agent has a clearly-labeled fallback. LIVE vs FALLBACK is shown on every data widget.

### 3. Start the backend
```bash
uvicorn main:app --reload --port 8000
```
Confirm it's alive: http://localhost:8000/api/health → {"status":"ok","llm_enabled":false}

Browse the auto-generated API docs: http://localhost:8000/docs

### 4. Open the frontend
Open `frontend/index.html` directly in your browser — no build step, no server needed.

The sidebar will show **"backend online · heuristic mode"** when the frontend connects successfully.

## API Endpoints
| Endpoint | What it does |
|---|---|
| `GET /api/health` | Backend status + LLM mode |
| `GET /api/cities` | List of all cities and zones |
| `GET /api/city/{id}/overview` | Parallel AQI + attribution for all 10 zones |
| `GET /api/city/{id}/zone/{z}/attribution` | Full source decomposition + causal narrative |
| `GET /api/city/{id}/zone/{z}/forecast` | 72h CAMS forecast + Holt-Winters backtest |
| `GET /api/city/{id}/enforcement` | Ranked zones with dispersion + upwind targets |
| `GET /api/city/{id}/zone/{z}/advisory?lang=` | Health advisory in regional language |
| `GET /api/city/{id}/validation` | Attribution vs published study comparison |
| `GET /api/city/{id}/zone/{z}/pipeline` | Full pipeline run, measured wall-clock |

## Data Sources
### Real, keyless (always live)
| Source | What we fetch | Used by |
|---|---|---|
| **Open-Meteo Weather API** | Wind speed, direction, temperature, humidity (72h forecast) | Attribution Agent, Enforcement Agent, dispersion model |
| **Open-Meteo Air Quality API** | PM2.5, PM10, NO2, O3, US AQI — CAMS-backed forecast + 92-day history | Forecast Agent, Attribution Agent |
| **OSM Overpass API** | Industrial zones, construction sites, schools, hospitals, major roads | Attribution Agent, Advisory Agent, Enforcement Agent |

### Real, requires free key
| Source | What we fetch | Used by |
|---|---|---|
| **NASA FIRMS (VIIRS SNPP NRT)** | Satellite thermal anomalies and active fires within 15km | Attribution Agent (biomass/burning signal) |
| **TomTom Traffic Flow API** | Real-time road congestion % at zone coordinates | Attribution Agent (vehicular signal) |
| **OpenAQ v3 API** | Nearest CAAQMS ground station reading (PM2.5) | Attribution Agent (station validation) |

### Optional (LLM upgrade)
| Source | What changes |
|---|---|
| **Anthropic Claude API** | Attribution Agent and Advisory Agent call `reason_with_llm()` — produces real LLM-generated causal reasoning and contextual advisories instead of heuristic/template fallback. Zero code changes needed — set `ANTHROPIC_API_KEY` in `.env` and restart. |

## How the Attribution Works (Q1 in Detail)
The causal narrative ("the air is bad because a construction site 1.9km east is upwind right now") is built from:
1. **Real OSM coordinates** for every industrial/construction feature within 1.5km, fetched via Overpass
2. **Haversine distance** and **compass bearing** from the zone centre to each feature
3. **Live wind direction** from Open-Meteo — checking if the wind is blowing FROM that bearing TOWARD the zone (within a 50° tolerance)
4. **PM2.5:NO2 ratio** — a high ratio skews attribution toward dust/biomass over fresh vehicular exhaust
5. **Live traffic congestion** from TomTom — boosts vehicular share when congestion is high
6. **Satellite thermal anomaly count** from NASA FIRMS — boosts biomass/waste-burning share

## How the Forecast Works (Q2 in Detail)
- **Forward forecast**: Open-Meteo Air Quality API (CAMS-backed atmospheric chemical-transport model) — a genuine third-party atmospheric model, not something we wrote
- **Backtest**: Our own Holt-Winters additive model (level + trend + 24h seasonal profile, `alpha=0.85`) trained on the 5-day real historical window and evaluated on a 24-hour holdout
- **Comparison**: Model RMSE vs naive persistence baseline (last observed value repeated), reported honestly — including when the model loses on a sharp regime shift

## Reliability Design
### Circuit breaker
OSM Overpass is a free, shared public service that can be slow or unavailable. After 2 consecutive failures, the circuit breaker opens and all subsequent zone calls return a labeled fallback instantly (instead of waiting out the full timeout every time). Auto-retries after a 120s cooldown.

### In-memory TTL cache
All external API responses are cached for 30 minutes. For a demo session: visit every tab once to warm the cache, then all subsequent interactions are near-instant.

### Parallel zone processing
All 10-zone endpoints (Enforcement, Validation, city overview) use `ThreadPoolExecutor` to process zones concurrently rather than sequentially — measured 10x speedup over the original sequential design.

### LIVE / FALLBACK provenance
Every data widget in the frontend shows a green LIVE or orange FALLBACK badge indicating whether its data came from a real API call or a seeded deterministic fallback. Nothing pretends to be real.

## Validation Against Published Research
The Validation Agent compares our city-wide averaged attribution against a real, independently published source-apportionment study for each city:
| City | Reference study |
|---|---|
| Delhi | Comprehensive Study on Air Pollution and GHGs in Delhi (IIT Kanpur / DPCC) |
| Mumbai | Air Quality Assessment, Emissions Inventory & Source Apportionment (CPCB/MCGM) |
| Kolkata | PM10/PM2.5 Source Apportionment Study & Emission Inventory (WBPCB) |
| Bengaluru | TERI source-apportionment study (as reported by Deccan Herald) |
| Chennai | What Makes the Indian Megacity Chennai's Air Unhealthy? (AAQR, 2024) |

**Honest limitation**: Published studies for the same city can disagree with each other by large margins. We only score against categories each study actually reported, and explicitly flag the rest as having no independent benchmark rather than fabricating full coverage.

## Evaluation Focus Coverage
| Criterion | Implementation |
|---|---|
| Source attribution accuracy vs emission inventories | Validation Agent — real published studies, honest MAE, partial-coverage flagging |
| AQI forecast accuracy (RMSE vs persistence) | Forecast Agent — Holt-Winters, real historical backtest, honest reporting |
| Enforcement recommendation quality | Enforcement Agent — real OSM targets, real dispersion, real wind |
| Citizen advisory relevance + language coverage | Advisory Agent — 5 languages, real vulnerability layer, LLM-ready |
| Reduction in response time: signal → intervention | Pipeline endpoint — real measured wall-clock, full 5-stage trace |

## Known Limitations (stated plainly)
- **Overpass availability**: OSM Overpass is a free public service and can be slow or unavailable. The circuit breaker handles this gracefully but can't guarantee live land-use data on every request.
- **Simplified dispersion model**: Steady-state Gaussian plume (Pasquill-Gifford rural coefficients). Real regulatory-grade models (AERMOD, CALPUFF) account for terrain and building downwash — this is genuine physics, not decorative, but not production-grade.
- **Sharp regime-shift forecasting**: The Holt-Winters model can lose to naive persistence immediately after an unpredictable pollution episode starts or clears. This is a known, honest statistical limitation, surfaced in the UI rather than hidden.
- **Sentinel-5P / MODIS imagery**: Not yet integrated. NASA FIRMS thermal anomalies are used as a satellite proxy for biomass/burning detection.
- **Census-tract population data**: Exposure scoring uses OSM school/hospital density as a proxy for population vulnerability rather than actual census-tract data.

## Deliverables
| Deliverable | Status |
|---|---|
| Working Prototype | ✅ Complete — FastAPI backend + browser frontend |
| Architecture Diagram | ✅ Complete — PNG |
| Presentation Deck | ✅ Complete — 10-slide PPTX |
| Demo Video | ✅ Complete |

## Built With
- [FastAPI](https://fastapi.tiangolo.com/)
- [Open-Meteo](https://open-meteo.com/)
- [OpenStreetMap Overpass API](https://overpass-api.de/)
- [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/)
- [TomTom Traffic API](https://developer.tomtom.com/)
- [OpenAQ](https://openaq.org/)
- [Anthropic Claude](https://www.anthropic.com/) *(LLM hook, activates with key)*
- [Chart.js](https://www.chartjs.org/)

*ET AI Hackathon 2.0 — Round 2 Build Sprint · AI-Powered Urban Air Quality Intelligence for Smart City Intervention*