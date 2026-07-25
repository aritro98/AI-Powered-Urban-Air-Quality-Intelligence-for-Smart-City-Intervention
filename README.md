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
Refer to the [diagram](./diagram/) directory for the full workflow.