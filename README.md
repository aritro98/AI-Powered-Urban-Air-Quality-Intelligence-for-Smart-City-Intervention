# AQI-Sentinel: AI-Powered Urban Air Quality Intelligence for Smart City Intervention

> *From "the air is dirty, here are the numbers" → "the air will be dangerous tomorrow in this area because of these sources — here is where to send enforcement teams today."*

**Theme:** Smart Cities / Environmental Intelligence / Geospatial Analytics / Public Health

## What This Is
India has over 900 Continuous Ambient Air Quality Monitoring Stations (CAAQMS) deployed under the National Clean Air Programme. A 2024 CAG audit found that only 31% of cities with monitoring data had any actionable multi-agency response protocol linked to those readings.

**The data exists. The intelligence layer to act on it does not.**

AQI-Sentinel is a 6-agent AI platform that fuses real monitoring station data, satellite imagery, mobility feeds, meteorological forecasts, and geospatial land-use layers to answer three questions city administrators actually need:

| Question | Agent | How |
|---|---|---|
| **Why is the air bad here, right now?** | Attribution Agent | Real wind bearing + real OSM land-use → names a specific upwind source, not a category percentage |
| **How bad will it be in 24-72 hours?** | Forecast Agent | Holt-Winters model on real historical AQI, honestly backtested against a persistence baseline |
| **Where should officials go right now?** | Enforcement Agent | Severity × confidence × exposure ranking + real Gaussian-plume dispersion + real upwind target |

## Architecture
Refer to the [diagram](./diagram/) directory to view the full architecture.
Supporting modules: `geo_utils.py` · `models/dispersion.py` · `models/timeseries.py` · `reference_data.py`
Reliability: `cache.py` (30-min TTL) · `circuit_breaker.py` (opens after 2 failures, 120s cooldown)

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