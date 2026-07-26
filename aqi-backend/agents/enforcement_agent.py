"""
EnforcementAgent — ranks zones for inspector dispatch AND (this is the
fix for the brief's Q3: "where should officials go RIGHT NOW to fix it
fastest") surfaces a single, specific, real primary target per zone --
the nearest real industrial/construction feature that is currently
upwind, per AttributionAgent's wind analysis -- instead of only ranking
zones and leaving officials to guess where within the zone to actually go.

Falls back honestly to "no specific upwind target identified" when the
real data doesn't support naming one, rather than inventing a plausible-
looking target.

All 10 zones are processed CONCURRENTLY (see concurrency.py) rather than
one after another -- with 10 zones each potentially waiting on several
external APIs, sequential processing was the main cause of multi-minute
load times; this turns that into roughly the slowest single zone's time.
"""
from agents.base_agent import BaseAgent
from agents.attribution_agent import AttributionAgent
from agents.data_agent import DataAgent
from models import dispersion
from concurrency import run_parallel
import cities


class EnforcementAgent(BaseAgent):
    name = "EnforcementAgent"

    def run(self, city_id):
        attribution_agent = AttributionAgent(self.trace)
        data_agent = DataAgent(self.trace)

        def process_zone(zone):
            lat, lon = cities.zone_coords(city_id, zone)
            attribution = attribution_agent.run(city_id, zone)
            weather = data_agent.fetch_weather(lat, lon)
            landuse = data_agent.fetch_landuse_and_pois(lat, lon)

            top_source = max(attribution["shares"], key=attribution["shares"].get)
            top_confidence = attribution["confidence"][top_source]
            severity = min(1.0, attribution["aqi"] / 400)
            exposure = min(1.0, (attribution["signals"]["construction_sites"] * 0 + 1) * 0.4
                           + min(attribution["signals"].get("industrial_sites", 0), 5) * 0.05 + 0.3)

            wind_speed_ms = (weather["wind_speed_kmh"][0] if weather["wind_speed_kmh"] else 10) / 3.6
            stability = dispersion.stability_class_from_wind(wind_speed_ms)
            emission_rate = dispersion.estimate_emission_rate(
                attribution["signals"]["industrial_sites"],
                attribution["signals"]["construction_sites"],
                attribution["aqi"],
            )
            plume = dispersion.ground_level_concentration(
                Q_g_s=emission_rate,
                wind_speed_ms=wind_speed_ms,
                stability_class=stability,
                stack_height_m=25,
                distances_m=[250, 500, 1000, 2000],
            )

            # The Q3 fix: pick the single nearest REAL currently-upwind
            # source as the specific dispatch target, if one exists.
            active_upwind = [s for s in attribution["upwind_sources"] if s["is_upwind_now"]]
            primary_target = active_upwind[0] if active_upwind else None

            score = round((severity * 0.5 + top_confidence * 0.3 + exposure * 0.2) * 100)
            return {
                "zone": zone,
                "score": score,
                "aqi": attribution["aqi"],
                "aqi_source": attribution["aqi_source"],
                "top_source": top_source,
                "top_source_confidence": top_confidence,
                "wind_speed_ms": round(wind_speed_ms, 1),
                "wind_source": weather["source"],
                "stability_class": stability,
                "plume_ug_m3_at_250_500_1000_2000m": plume,
                "industrial_sites": attribution["signals"]["industrial_sites"],
                "construction_sites": attribution["signals"]["construction_sites"],
                "evidence_source": landuse["source"],
                "industrial_refs": landuse.get("industrial_refs", []),
                "construction_refs": landuse.get("construction_refs", []),
                "primary_target": primary_target,
                "causal_narrative": attribution["causal_narrative"],
            }

        zones = cities.CITIES[city_id]["zones"]
        results = run_parallel(zones, process_zone)

        results.sort(key=lambda r: r["score"], reverse=True)
        self.log("rank_zones", "internal", f"ranked {len(results)} zones by severity x confidence x exposure")
        return results[:8]