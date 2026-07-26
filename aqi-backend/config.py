"""
Central configuration for AQI-Sentinel backend.

Nothing here requires a paid key to run. USE_LLM flips on automatically
the moment ANTHROPIC_API_KEY is present in the environment / .env file —
no code changes needed elsewhere.
"""
import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
OPENAQ_API_KEY = os.getenv("OPENAQ_API_KEY", "").strip()
NASA_FIRMS_MAP_KEY = os.getenv("NASA_FIRMS_MAP_KEY", "").strip()
TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY", "").strip()

USE_LLM = bool(ANTHROPIC_API_KEY)
ANTHROPIC_MODEL = "claude-sonnet-4-5"

# Network behaviour
REQUEST_TIMEOUT_SECONDS = 6
CACHE_TTL_SECONDS = 1800  # 30 min: once you've "warmed" the app by visiting each tab once

# External endpoints (all free / keyless unless noted)
OPEN_METEO_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_MIRROR_URL = "https://overpass.kumi.systems/api/interpreter"
OVERPASS_TIMEOUT_SECONDS = 5
USER_AGENT = "AQI-Sentinel/1.0 (ET AI Hackathon prototype; educational, low-volume)"

# Requires a free API key: https://firms.modis.gsfc.nasa.gov/api/map_key/
NASA_FIRMS_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

# Requires a free API key (2,500 free daily calls): https://developer.tomtom.com/
TOMTOM_FLOW_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"

# Requires a free API key: https://explore.openaq.org/register
OPENAQ_BASE_URL = "https://api.openaq.org/v3"