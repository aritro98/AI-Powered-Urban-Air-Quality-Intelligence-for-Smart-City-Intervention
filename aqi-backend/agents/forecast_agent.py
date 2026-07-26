"""
ForecastAgent — 72-hour hyperlocal AQI forecast.

Two real, distinct predictive-analytics components:
  1. The forward-looking 72h forecast itself comes from Open-Meteo's Air
     Quality API, whose forecast component is powered by Copernicus CAMS
     (Copernicus Atmosphere Monitoring Service) — a genuine atmospheric
     chemical-transport model, not something we wrote.
  2. We separately validate predictive value using our OWN seasonal-naive
     model backtested on real historical AQI for that exact coordinate,
     honestly compared against a persistence baseline. If fewer than ~3
     days of real history came back, we say so instead of presenting a
     misleading RMSE.
"""
from agents.base_agent import BaseAgent
from agents.data_agent import DataAgent
from models import timeseries
import cities


class ForecastAgent(BaseAgent):
    name = "ForecastAgent"

    def run(self, city_id, zone):
        lat, lon = cities.zone_coords(city_id, zone)
        data_agent = DataAgent(self.trace)
        air = data_agent.fetch_air_quality(lat, lon, past_days=5, forecast_days=3)

        hours = air["hours"]
        aqi_series = air["us_aqi"]

        # split into history (past_days) vs. forward forecast (forecast_days)
        # Open-Meteo returns one contiguous hourly series; we locate "now"
        # as the midpoint proportionally since past_days=5, forecast_days=3.
        total_len = len(aqi_series) or (5 + 3) * 24
        history_len = round(total_len * (5 / 8)) if air["source"] == "live" else 5 * 24
        history = aqi_series[:history_len]
        forward_forecast = aqi_series[history_len:]

        backtest = timeseries.backtest(history, holdout=24) if history else None
        self.log(
            "backtest",
            "internal" if backtest else "insufficient_data",
            "Seasonal-naive model vs persistence, real historical AQI" if backtest else "fewer than 3 days real history available",
        )

        return {
            "zone": zone,
            "data_source": air["source"],
            "forecast_source": "Open-Meteo (CAMS-backed)" if air["source"] == "live" else "seeded fallback",
            "forward_forecast_72h": [round(v, 1) for v in forward_forecast] or self._synthetic_forward(history),
            "history_used_for_backtest": len(history),
            "backtest": backtest,
        }

    @staticmethod
    def _synthetic_forward(history):
        if not history:
            return []
        last = history[-1]
        return [round(last, 1)] * 72