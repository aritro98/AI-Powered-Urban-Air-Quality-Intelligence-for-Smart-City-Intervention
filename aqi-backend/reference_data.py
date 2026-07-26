"""
Real published source-apportionment reference data, one study per city,
found via web search (not fabricated). Used to validate our own
attribution output against independent ground truth.

IMPORTANT HONESTY NOTE, read before changing this file:
Published source-apportionment studies for Indian cities disagree with
each other substantially -- e.g. published Delhi vehicular-PM2.5 estimates
range from ~12% to ~47% depending on the study, methodology and year.
There is no single agreed "ground truth" in the scientific literature.
Rather than force a fake clean comparison across all 6 of our categories,
each city's reference here only includes the categories that particular
study actually reported. AttributionAgent validation should compare only
on overlapping categories and explicitly flag the rest as unvalidated --
see agents/validation_agent.py.

Category mapping notes (approximate, documented per city below):
our "Road & Fugitive Dust" ~ published "road dust" / "soil dust"
our "Biomass / Waste Burning" ~ published "domestic fuel burning" / "open
    waste burning" / "biomass burning" (these are not identical concepts,
    but are the closest available analogues)
"""

REFERENCE_STUDIES = {
    "delhi": {
        "study": "Comprehensive Study on Air Pollution and GHGs in Delhi (IIT Kanpur / DPCC)",
        "url": "https://cerca.iitd.ac.in/uploads/Reports/1576211826iitk.pdf",
        "pollutant": "PM2.5",
        "benchmarks": {
            "Road & Fugitive Dust": 38.0,
            "Vehicular": 20.0,
            "Biomass / Waste Burning": 12.0,  # reported as "domestic fuel burning"
        },
        "note": "Industrial, Construction and Regional Transport shares were not "
                "separately quantified as city-wide PM2.5 percentages in this study.",
    },
    "mumbai": {
        "study": "Air Quality Assessment, Emissions Inventory & Source Apportionment for Mumbai (CPCB/MCGM)",
        "url": "https://cpcb.nic.in/actionplan/mumbai.pdf",
        "pollutant": "PM (city emission inventory)",
        "benchmarks": {
            "Industrial": 33.0,
        },
        "note": "Only the industrial-sector emission share was reported as a clean "
                "city-wide percentage in this official action plan; vehicular and "
                "road-dust shares were reported qualitatively ('well distributed "
                "amongst') rather than as single city-wide numbers, so are excluded "
                "here rather than guessed.",
    },
    "kolkata": {
        "study": "PM10/PM2.5 Source Apportionment Study & Emission Inventory for Kolkata & Howrah (WBPCB)",
        "url": "https://www.wbpcb.gov.in/writereaddata/files/SA_Kol-How_Final%20Report.pdf",
        "pollutant": "PM10",
        "benchmarks": {
            "Biomass / Waste Burning": 35.0,  # reported as domestic + commercial combustion
            "Vehicular": 22.0,
            "Road & Fugitive Dust": 10.0,
        },
        "note": "Industrial and Construction shares were not separately broken out "
                "as city-wide percentages in this study for Kolkata proper.",
    },
    "bengaluru": {
        "study": "TERI source-apportionment study for Bengaluru (as reported by Deccan Herald)",
        "url": "https://www.deccanherald.com/india/karnataka/bengaluru/bengaluru-situation-is-grim-when-it-comes-to-air-pollution-859388.html",
        "pollutant": "PM10",
        "benchmarks": {
            "Vehicular": 42.0,
            "Road & Fugitive Dust": 20.0,
            "Construction": 14.0,
            "Industrial": 14.0,
        },
        "note": "DG sets (7%) and domestic (3%) shares reported by the study don't "
                "map to any of our 6 categories, so are omitted rather than folded "
                "in arbitrarily.",
    },
    "chennai": {
        "study": "What Makes the Indian Megacity Chennai's Air Unhealthy? (Aerosol and Air Quality Research, 2024)",
        "url": "https://aaqr.org/articles/aaqr-24-03-oa-0089",
        "pollutant": "PM10",
        "benchmarks": {
            "Vehicular": 23.0,
            "Industrial": 20.0,
            "Biomass / Waste Burning": 13.0,  # reported as open burning of MSW
        },
        "note": "Construction, Road Dust and Regional Transport shares were not "
                "separately quantified as city-wide percentages in this study.",
    },
}