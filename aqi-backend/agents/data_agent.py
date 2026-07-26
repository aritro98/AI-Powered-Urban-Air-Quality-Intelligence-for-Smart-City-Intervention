"""
DataAgent — the only agent that talks to the outside world.

Every fetch method returns a dict with an explicit "source" field:
    "source": "live"      -> real data just retrieved from a public API
    "source": "fallback"  -> API unreachable / rate-limited; seeded
                             synthetic values returned instead, clearly
                             flagged so nothing masquerades as real.

This keeps every downstream agent honest about data provenance, and lets
the frontend show a "Live" / "Fallback" badge per widget.
"""
import hashlib
import math
import requests

from config import (
    OPEN_METEO_WEATHER_URL,
    OPEN_METEO_AIR_QUALITY_URL,
    OVERPASS_URL,
    OVERPASS_MIRROR_URL,
    OVERPASS_TIMEOUT_SECONDS,
    USER_AGENT,
    REQUEST_TIMEOUT_SECONDS,
    NASA_FIRMS_MAP_KEY,
    NASA_FIRMS_URL,
    TOMTOM_API_KEY,
    TOMTOM_FLOW_URL,
    OPENAQ_API_KEY,
    OPENAQ_BASE_URL,
)
from cache import cache_get, cache_set
from agents.base_agent import BaseAgent
from geo_utils import haversine_km
import geo_utils
from circuit_breaker import CircuitBreaker

_overpass_breaker = CircuitBreaker(failure_threshold=2, cooldown_seconds=120)

def _seed(*parts):
    h = hashlib.md5("::".join(str(p) for p in parts).encode()).hexdigest()
    return int(h[:8], 16)


def _seeded_uniform(seed, lo, hi):
    # deterministic pseudo-random fallback value, stable across requests
    frac = (seed % 10_000) / 10_000
    return lo + frac * (hi - lo)


class DataAgent(BaseAgent):
    name = "DataAgent"

    def _log(self, action, source, detail=""):
        self.log(action, source, detail)

    # ------------------------------------------------------------------
    # Weather (real, keyless): https://open-meteo.com
    # ------------------------------------------------------------------
    def fetch_weather(self, lat, lon):
        key = f"weather::{lat}::{lon}"
        cached = cache_get(key)
        if cached:
            self._log("fetch_weather", cached["source"], "cache hit")
            return cached
        try:
            resp = requests.get(
                OPEN_METEO_WEATHER_URL,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m",
                    "forecast_days": 3,
                    "timezone": "auto",
                },
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            data = resp.json()
            result = {
                "source": "live",
                "hours": data["hourly"]["time"],
                "temperature_c": data["hourly"]["temperature_2m"],
                "humidity_pct": data["hourly"]["relative_humidity_2m"],
                "wind_speed_kmh": data["hourly"]["wind_speed_10m"],
                "wind_direction_deg": data["hourly"]["wind_direction_10m"],
            }
            self._log("fetch_weather", "live", "open-meteo forecast API")
            return cache_set(key, result)
        except Exception as exc:
            seed = _seed(lat, lon, "weather")
            result = {
                "source": "fallback",
                "hours": [],
                "temperature_c": [_seeded_uniform(seed, 18, 34)] * 72,
                "humidity_pct": [_seeded_uniform(seed + 1, 35, 85)] * 72,
                "wind_speed_kmh": [_seeded_uniform(seed + 2, 3, 22)] * 72,
                "wind_direction_deg": [_seeded_uniform(seed + 3, 0, 359)] * 72,
                "error": str(exc),
            }
            self._log("fetch_weather", "fallback", f"open-meteo unreachable: {exc}")
            return result

    # ------------------------------------------------------------------
    # Air quality (real, keyless): Open-Meteo Air Quality API.
    # Forecast component is powered upstream by Copernicus CAMS.
    # past_days gives real historical AQI for honest backtesting.
    # ------------------------------------------------------------------
    def fetch_air_quality(self, lat, lon, past_days=5, forecast_days=3):
        key = f"aq::{lat}::{lon}::{past_days}::{forecast_days}"
        cached = cache_get(key)
        if cached:
            self._log("fetch_air_quality", cached["source"], "cache hit")
            return cached
        try:
            resp = requests.get(
                OPEN_METEO_AIR_QUALITY_URL,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "hourly": "pm2_5,pm10,nitrogen_dioxide,ozone,us_aqi",
                    "past_days": past_days,
                    "forecast_days": forecast_days,
                    "timezone": "auto",
                },
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            data = resp.json()
            result = {
                "source": "live",
                "hours": data["hourly"]["time"],
                "pm2_5": data["hourly"]["pm2_5"],
                "pm10": data["hourly"]["pm10"],
                "no2": data["hourly"]["nitrogen_dioxide"],
                "ozone": data["hourly"]["ozone"],
                "us_aqi": data["hourly"]["us_aqi"],
            }
            self._log("fetch_air_quality", "live", "open-meteo air-quality API (CAMS-backed forecast)")
            return cache_set(key, result)
        except Exception as exc:
            # Real AQI is strongly autocorrelated + diurnal, unlike IID noise
            # (on which no model can beat persistence -- that would be a
            # correct but uselessly pessimistic demo). This AR(1)+diurnal
            # walk is a fair offline stand-in that still lets a real
            # forecasting model show genuine, honest skill.
            base = _seeded_uniform(_seed(lat, lon, "aqi-base"), 60, 260)
            n = (past_days + forecast_days) * 24
            level = base
            series = []
            for i in range(n):
                diurnal = math.sin((i % 24) / 24 * 2 * math.pi - math.pi / 2) * 18
                drift = _seeded_uniform(_seed(lat, lon, "aqi-drift", i), -6, 6)
                level = level * 0.85 + (base + diurnal) * 0.15 + drift * 0.2
                series.append(round(max(15, level), 1))
            result = {
                "source": "fallback",
                "hours": [],
                "pm2_5": series,
                "pm10": [v * 1.6 for v in series],
                "no2": [v * 0.3 for v in series],
                "ozone": [v * 0.5 for v in series],
                "us_aqi": series,
                "error": str(exc),
            }
            self._log("fetch_air_quality", "fallback", f"open-meteo air-quality unreachable: {exc}")
            return result

    # ------------------------------------------------------------------
    # Land use + points of interest (real, keyless): OpenStreetMap Overpass
    # ------------------------------------------------------------------
    def fetch_landuse_and_pois(self, lat, lon, radius_m=1500):
        key = f"osm::{lat}::{lon}::{radius_m}"
        cached = cache_get(key)
        if cached:
            self._log("fetch_landuse_and_pois", cached["source"], "cache hit")
            return cached

        if _overpass_breaker.is_open():
            # Overpass has failed repeatedly -- don't pay the full timeout
            # cost again on every zone/tab while it's known to be down.
            # This is the real fix for "still slow even with fallback":
            # failing fast beats failing slow, especially at scale (10
            # zones x multiple tabs). Auto-retries after the cooldown.
            result = self._osm_fallback(lat, lon, f"circuit breaker open, retrying in {_overpass_breaker.seconds_until_retry()}s")
            self._log("fetch_landuse_and_pois", "fallback", f"Overpass circuit breaker open (retry in {_overpass_breaker.seconds_until_retry()}s)")
            return result

        try:
            result = self._overpass_counts(lat, lon, radius_m)
            _overpass_breaker.record_success()
            self._log("fetch_landuse_and_pois", "live", "OSM Overpass API")
            return cache_set(key, result)
        except Exception as exc:
            _overpass_breaker.record_failure()
            result = self._osm_fallback(lat, lon, str(exc))
            self._log("fetch_landuse_and_pois", "fallback", f"overpass unreachable: {exc}")
            return result

    @staticmethod
    def _osm_fallback(lat, lon, reason):
        seed = _seed(lat, lon, "osm")
        return {
            "source": "fallback",
            "industrial_sites": int(_seeded_uniform(seed, 0, 5)),
            "construction_sites": int(_seeded_uniform(seed + 1, 0, 9)),
            "schools": int(_seeded_uniform(seed + 2, 1, 9)),
            "hospitals": int(_seeded_uniform(seed + 3, 0, 4)),
            "major_roads": int(_seeded_uniform(seed + 4, 1, 8)),
            "industrial_refs": [],
            "construction_refs": [],
            "error": reason,
        }

    def _overpass_counts(self, lat, lon, radius_m):
        """Run one compact Overpass query and count tags client-side --
        more robust across Overpass mirrors than relying on `out count`
        ordering. Also keeps a sample of real OSM element IDs, tags AND
        COORDINATES for industrial/construction features, so we can later
        compute real bearing/distance from the zone centre and connect
        them to real wind direction (see AttributionAgent) -- this is
        what makes "why is the air bad HERE right now" answerable with an
        actual nearby source instead of just a category percentage.

        Uses a bounding-box filter rather than Overpass's 'around' filter:
        'around' forces the server to compute exact geometric distance for
        every candidate feature, which is genuinely expensive server-side
        (not just a network issue) and was the real cause of persistent
        timeouts even against a second mirror. A bbox is a cheap indexed
        range query. We then re-filter every result by the TRUE circular
        radius ourselves (haversine_km), so accuracy is unaffected --
        only Overpass's workload is reduced.

        overpass-api.de is a single free, heavily-shared public instance
        that is commonly slow or rejects anonymous-looking traffic. We
        send a proper identifying User-Agent (Overpass operators explicitly
        ask for this), and try a second public mirror before giving up."""
        south, west, north, east = geo_utils.bbox_from_point(lat, lon, radius_m)
        bbox = f"{south},{west},{north},{east}"
        query = f"""
        [out:json][timeout:20];
        (
          way["landuse"="industrial"]({bbox});
          way["landuse"="construction"]({bbox});
          node["amenity"="school"]({bbox});
          node["amenity"="hospital"]({bbox});
          way["highway"~"motorway|trunk|primary"]({bbox});
        );
        out tags center;
        """
        headers = {"User-Agent": USER_AGENT}
        last_exc = None
        for url in (OVERPASS_URL, OVERPASS_MIRROR_URL):
            try:
                resp = requests.post(url, data={"data": query}, headers=headers, timeout=OVERPASS_TIMEOUT_SECONDS)
                resp.raise_for_status()
                elements = resp.json().get("elements", [])
                return self._parse_overpass_elements(elements, lat, lon, radius_m)
            except Exception as exc:
                last_exc = exc
                continue
        raise last_exc

    @staticmethod
    def _parse_overpass_elements(elements, center_lat, center_lon, radius_m):
        counts = {"industrial_sites": 0, "construction_sites": 0, "schools": 0, "hospitals": 0, "major_roads": 0}
        industrial_refs, construction_refs = [], []
        radius_km = radius_m / 1000.0
        for el in elements:
            tags = el.get("tags", {})
            osm_type = el.get("type", "way")
            osm_id = el.get("id")
            osm_url = f"https://www.openstreetmap.org/{osm_type}/{osm_id}"
            name = tags.get("name")
            el_lat = el.get("lat") or el.get("center", {}).get("lat")
            el_lon = el.get("lon") or el.get("center", {}).get("lon")
            if el_lat is not None and el_lon is not None:
                if haversine_km(center_lat, center_lon, el_lat, el_lon) > radius_km:
                    continue
            if tags.get("landuse") == "industrial":
                counts["industrial_sites"] += 1
                if len(industrial_refs) < 5:
                    industrial_refs.append({"osm_type": osm_type, "osm_id": osm_id, "osm_url": osm_url,
                                             "name": name, "lat": el_lat, "lon": el_lon})
            elif tags.get("landuse") == "construction":
                counts["construction_sites"] += 1
                if len(construction_refs) < 5:
                    construction_refs.append({"osm_type": osm_type, "osm_id": osm_id, "osm_url": osm_url,
                                               "name": name, "lat": el_lat, "lon": el_lon})
            elif tags.get("amenity") == "school":
                counts["schools"] += 1
            elif tags.get("amenity") == "hospital":
                counts["hospitals"] += 1
            elif tags.get("highway") in ("motorway", "trunk", "primary"):
                counts["major_roads"] += 1
        counts["source"] = "live"
        counts["industrial_refs"] = industrial_refs
        counts["construction_refs"] = construction_refs
        return counts

    # ------------------------------------------------------------------
    # Satellite thermal anomalies / active fires (real, needs free key):
    # NASA FIRMS -- https://firms.modis.gsfc.nasa.gov/api/map_key/
    # Direct proxy for biomass/waste burning and industrial hot-spots
    # visible from space, right now.
    # ------------------------------------------------------------------
    def fetch_thermal_anomalies(self, lat, lon, radius_km=15, day_range=1):
        key = f"firms::{lat}::{lon}::{radius_km}::{day_range}"
        cached = cache_get(key)
        if cached:
            self._log("fetch_thermal_anomalies", cached["source"], "cache hit")
            return cached
        if not NASA_FIRMS_MAP_KEY:
            result = self._thermal_fallback(lat, lon, "no NASA_FIRMS_MAP_KEY configured")
            self._log("fetch_thermal_anomalies", "fallback", "no NASA_FIRMS_MAP_KEY configured")
            return result
        try:
            deg = radius_km / 111.0  # ~111km per degree latitude, close enough for a bbox
            west, south, east, north = lon - deg, lat - deg, lon + deg, lat + deg
            url = f"{NASA_FIRMS_URL}/{NASA_FIRMS_MAP_KEY}/VIIRS_SNPP_NRT/{west},{south},{east},{north}/{day_range}"
            resp = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
            resp.raise_for_status()
            lines = resp.text.strip().splitlines()
            if len(lines) < 2:
                result = {"source": "live", "count": 0, "points": []}
            else:
                header = lines[0].split(",")
                lat_i, lon_i = header.index("latitude"), header.index("longitude")
                frp_i = header.index("frp") if "frp" in header else None
                conf_i = header.index("confidence") if "confidence" in header else None
                points = []
                for line in lines[1:]:
                    cols = line.split(",")
                    plat, plon = float(cols[lat_i]), float(cols[lon_i])
                    if haversine_km(lat, lon, plat, plon) <= radius_km:
                        points.append({
                            "lat": plat, "lon": plon,
                            "frp": float(cols[frp_i]) if frp_i is not None else None,
                            "confidence": cols[conf_i] if conf_i is not None else None,
                        })
                result = {"source": "live", "count": len(points), "points": points[:10]}
            self._log("fetch_thermal_anomalies", "live", f"NASA FIRMS VIIRS, {result['count']} anomalies within {radius_km}km")
            return cache_set(key, result)
        except Exception as exc:
            result = self._thermal_fallback(lat, lon, str(exc))
            self._log("fetch_thermal_anomalies", "fallback", f"FIRMS unreachable: {exc}")
            return result

    def _thermal_fallback(self, lat, lon, reason):
        seed = _seed(lat, lon, "firms")
        return {"source": "fallback", "count": int(_seeded_uniform(seed, 0, 4)), "points": [], "error": reason}

    # ------------------------------------------------------------------
    # Real-time traffic congestion (real, needs free key):
    # TomTom Traffic Flow API -- https://developer.tomtom.com/
    # ------------------------------------------------------------------
    def fetch_traffic_flow(self, lat, lon):
        key = f"traffic::{lat}::{lon}"
        cached = cache_get(key)
        if cached:
            self._log("fetch_traffic_flow", cached["source"], "cache hit")
            return cached
        if not TOMTOM_API_KEY:
            result = self._traffic_fallback(lat, lon, "no TOMTOM_API_KEY configured")
            self._log("fetch_traffic_flow", "fallback", "no TOMTOM_API_KEY configured")
            return result
        try:
            resp = requests.get(
                TOMTOM_FLOW_URL,
                params={"point": f"{lat},{lon}", "unit": "KMPH", "key": TOMTOM_API_KEY},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            data = resp.json()["flowSegmentData"]
            current, free_flow = data["currentSpeed"], data["freeFlowSpeed"]
            congestion_pct = round(max(0, (1 - current / free_flow)) * 100, 1) if free_flow else 0.0
            result = {
                "source": "live",
                "congestion_pct": congestion_pct,
                "current_speed_kmh": current,
                "free_flow_speed_kmh": free_flow,
                "confidence": data.get("confidence"),
            }
            self._log("fetch_traffic_flow", "live", f"TomTom flow API, {congestion_pct}% congestion")
            return cache_set(key, result)
        except Exception as exc:
            result = self._traffic_fallback(lat, lon, str(exc))
            self._log("fetch_traffic_flow", "fallback", f"TomTom unreachable: {exc}")
            return result

    def _traffic_fallback(self, lat, lon, reason):
        seed = _seed(lat, lon, "traffic")
        return {"source": "fallback", "congestion_pct": round(_seeded_uniform(seed, 10, 65), 1),
                "current_speed_kmh": None, "free_flow_speed_kmh": None, "confidence": None, "error": reason}

    # ------------------------------------------------------------------
    # Ground-truth CAAQMS-network station reading (real, needs free key):
    # OpenAQ -- https://explore.openaq.org/register
    # ------------------------------------------------------------------
    def fetch_station_reading(self, lat, lon, radius_m=15000):
        key = f"openaq::{lat}::{lon}::{radius_m}"
        cached = cache_get(key)
        if cached:
            self._log("fetch_station_reading", cached["source"], "cache hit")
            return cached
        if not OPENAQ_API_KEY:
            result = {"source": "fallback", "station_name": None, "pm25": None, "error": "no OPENAQ_API_KEY configured"}
            self._log("fetch_station_reading", "fallback", "no OPENAQ_API_KEY configured")
            return result
        try:
            headers = {"X-API-Key": OPENAQ_API_KEY}
            loc_resp = requests.get(
                f"{OPENAQ_BASE_URL}/locations",
                params={"coordinates": f"{lat},{lon}", "radius": radius_m, "limit": 1},
                headers=headers, timeout=REQUEST_TIMEOUT_SECONDS,
            )
            loc_resp.raise_for_status()
            locations = loc_resp.json().get("results", [])
            if not locations:
                result = {"source": "live", "station_name": None, "pm25": None, "note": "no station within radius"}
                return cache_set(key, result)
            loc = locations[0]
            latest_resp = requests.get(
                f"{OPENAQ_BASE_URL}/locations/{loc['id']}/latest",
                headers=headers, timeout=REQUEST_TIMEOUT_SECONDS,
            )
            latest_resp.raise_for_status()
            measurements = latest_resp.json().get("results", [])
            pm25 = next((m["value"] for m in measurements if m.get("parameter", {}).get("name") == "pm25"), None)
            result = {"source": "live", "station_name": loc.get("name"), "pm25": pm25,
                       "station_distance_km": round(haversine_km(lat, lon, loc["coordinates"]["latitude"], loc["coordinates"]["longitude"]), 1)}
            self._log("fetch_station_reading", "live", f"OpenAQ station '{loc.get('name')}'")
            return cache_set(key, result)
        except Exception as exc:
            result = {"source": "fallback", "station_name": None, "pm25": None, "error": str(exc)}
            self._log("fetch_station_reading", "fallback", f"OpenAQ unreachable: {exc}")
            return result