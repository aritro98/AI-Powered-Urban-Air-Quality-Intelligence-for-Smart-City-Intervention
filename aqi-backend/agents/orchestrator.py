"""
Orchestrator — wires the five agents together per request and owns the
shared trace list that records every real step taken (which agent ran,
which external API it hit, live vs fallback). This trace is what the
frontend's "Agent Trace" panel renders — it is a genuine execution log,
not a scripted animation.
"""
from agents.attribution_agent import AttributionAgent
from agents.forecast_agent import ForecastAgent
from agents.enforcement_agent import EnforcementAgent
from agents.advisory_agent import AdvisoryAgent
from agents.data_agent import DataAgent
from agents.validation_agent import ValidationAgent
from concurrency import run_parallel
import cities
import time


class Orchestrator:
    def __init__(self):
        self.trace = []

    def _fresh_trace(self):
        self.trace = []
        return self.trace

    def city_overview(self, city_id):
        trace = self._fresh_trace()
        attribution_agent = AttributionAgent(trace)

        zones = cities.CITIES[city_id]["zones"]
        zone_results = run_parallel(zones, lambda zone: attribution_agent.run(city_id, zone))

        overall_aqi = round(sum(z["aqi"] for z in zone_results) / len(zone_results))
        return {
            "city": cities.CITIES[city_id]["name"],
            "overall_aqi": overall_aqi,
            "zones": zone_results,
            "trace": trace,
        }

    def zone_attribution(self, city_id, zone):
        trace = self._fresh_trace()
        result = AttributionAgent(trace).run(city_id, zone)
        result["trace"] = trace
        return result

    def zone_forecast(self, city_id, zone):
        trace = self._fresh_trace()
        result = ForecastAgent(trace).run(city_id, zone)
        result["trace"] = trace
        return result

    def enforcement(self, city_id):
        trace = self._fresh_trace()
        result = EnforcementAgent(trace).run(city_id)
        return {"ranked_zones": result, "trace": trace}

    def advisory(self, city_id, zone, lang):
        trace = self._fresh_trace()
        result = AdvisoryAgent(trace).run(city_id, zone, lang)
        result["trace"] = trace
        return result

    def validation(self, city_id):
        trace = self._fresh_trace()
        result = ValidationAgent(trace).run(city_id)
        result["trace"] = trace
        return result

    def full_pipeline(self, city_id, zone, lang):
        """Run Data -> Attribution -> Forecast -> Enforcement(single zone
        scope via Attribution reuse) -> Advisory sequentially for ONE zone,
        with a single shared trace, and measure real wall-clock elapsed
        time from the first logged step to the last. This is the genuine,
        measured "signal to intervention" response-time metric -- not an
        animated countdown."""
        trace = self._fresh_trace()
        wall_start = time.time()

        attribution = AttributionAgent(trace).run(city_id, zone)
        forecast = ForecastAgent(trace).run(city_id, zone)

        # Enforcement-style scoring for just this one zone (reuses the
        # attribution just computed rather than re-running all 10 zones,
        # since this endpoint is about timing one zone's full pipeline).
        lat, lon = cities.zone_coords(city_id, zone)
        data_agent = DataAgent(trace)
        weather = data_agent.fetch_weather(lat, lon)
        from models import dispersion
        wind_speed_ms = (weather["wind_speed_kmh"][0] if weather["wind_speed_kmh"] else 10) / 3.6
        stability = dispersion.stability_class_from_wind(wind_speed_ms)
        emission_rate = dispersion.estimate_emission_rate(
            attribution["signals"]["industrial_sites"],
            attribution["signals"]["construction_sites"],
            attribution["aqi"],
        )
        plume = dispersion.ground_level_concentration(
            Q_g_s=emission_rate, wind_speed_ms=wind_speed_ms,
            stability_class=stability, stack_height_m=25,
            distances_m=[250, 500, 1000, 2000],
        )
        trace.append({"agent": "EnforcementAgent", "action": "score_zone", "source": "internal",
                      "detail": "dispersion + severity scoring for single-zone pipeline run", "t": round(time.time(), 3)})

        advisory = AdvisoryAgent(trace).run(city_id, zone, lang)

        wall_end = time.time()
        first_t = trace[0]["t"] if trace else wall_start
        last_t = trace[-1]["t"] if trace else wall_end

        return {
            "zone": zone,
            "pipeline_seconds": round(wall_end - wall_start, 3),
            "trace_span_seconds": round(last_t - first_t, 3),
            "steps": len(trace),
            "stages": {
                "attribution_aqi": attribution["aqi"],
                "forecast_backtest_available": forecast["backtest"] is not None,
                "dispersion_stability_class": stability,
                "advisory_generated_by": advisory["generated_by"],
            },
            "trace": trace,
        }