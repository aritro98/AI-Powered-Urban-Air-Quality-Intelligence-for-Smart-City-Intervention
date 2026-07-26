"""
ValidationAgent — compares AQI-Sentinel's own source-attribution output
against a real, independently published source-apportionment study for
that city (see reference_data.py for citations).

Deliberately honest about partial coverage: published studies each report
a different subset of categories, using somewhat different definitions,
and different studies for the same city disagree with each other by large
margins (documented in reference_data.py). This agent only scores
agreement on categories the reference study actually reported, and
explicitly returns which categories have no independent benchmark at all,
rather than presenting a misleadingly complete-looking comparison.

All 10 zones are processed CONCURRENTLY (see concurrency.py), same fix as
EnforcementAgent -- see that file's docstring for why this matters.
"""
from agents.base_agent import BaseAgent
from agents.attribution_agent import AttributionAgent
from concurrency import run_parallel
import cities
import reference_data


class ValidationAgent(BaseAgent):
    name = "ValidationAgent"

    def run(self, city_id):
        ref = reference_data.REFERENCE_STUDIES.get(city_id)
        if not ref:
            self.log("validate", "internal", f"no reference study registered for {city_id}")
            return {"available": False}

        attribution_agent = AttributionAgent(self.trace)
        zones = cities.CITIES[city_id]["zones"]
        per_zone = run_parallel(zones, lambda zone: attribution_agent.run(city_id, zone))

        # city-wide average share per category, across all real zone results
        categories = per_zone[0]["shares"].keys()
        city_avg = {
            cat: round(sum(z["shares"][cat] for z in per_zone) / len(per_zone) * 100, 1)
            for cat in categories
        }

        comparisons = []
        errors = []
        for cat, our_pct in city_avg.items():
            published_pct = ref["benchmarks"].get(cat)
            if published_pct is None:
                comparisons.append({
                    "category": cat,
                    "our_pct": our_pct,
                    "published_pct": None,
                    "absolute_error": None,
                    "status": "no_independent_benchmark",
                })
            else:
                err = round(abs(our_pct - published_pct), 1)
                errors.append(err)
                comparisons.append({
                    "category": cat,
                    "our_pct": our_pct,
                    "published_pct": published_pct,
                    "absolute_error": err,
                    "status": "compared",
                })

        mae = round(sum(errors) / len(errors), 1) if errors else None
        self.log(
            "validate",
            "internal",
            f"compared {len(errors)}/{len(comparisons)} categories against '{ref['study']}'; MAE={mae}",
        )

        return {
            "available": True,
            "study": ref["study"],
            "study_url": ref["url"],
            "study_pollutant": ref["pollutant"],
            "study_note": ref["note"],
            "categories_compared": len(errors),
            "categories_total": len(comparisons),
            "mean_absolute_error_pct_points": mae,
            "comparisons": comparisons,
        }