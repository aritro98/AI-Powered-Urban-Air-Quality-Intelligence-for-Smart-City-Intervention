"""
Simplified Gaussian plume atmospheric dispersion model.

This is the standard steady-state Gaussian plume equation used in
introductory air-quality engineering (e.g. Turner's Workbook of
Atmospheric Dispersion Estimates). It is a deliberate simplification —
real regulatory-grade models (AERMOD, CALPUFF) account for terrain,
building downwash and non-steady meteorology — but the physics here
(dispersion coefficients growing with downwind distance, wind-speed
dilution, ground reflection) are genuine, not decorative.

    C(x, y, z) = Q / (2*pi*u*sigma_y*sigma_z)
                 * exp(-y^2 / (2*sigma_y^2))
                 * [exp(-(z-H)^2/(2*sigma_z^2)) + exp(-(z+H)^2/(2*sigma_z^2))]

Q  = emission rate (g/s)
u  = wind speed (m/s)
H  = effective stack height (m)
sigma_y, sigma_z = Pasquill-Gifford dispersion coefficients (function of
                   downwind distance x and atmospheric stability class)
"""
import math

# Pasquill-Gifford coefficients (rural, Briggs formulas), keyed by stability class A-F
_BRIGGS_RURAL = {
    "A": {"y": (0.22, 0.0001, -0.5), "z": (0.20, 0, 0)},
    "B": {"y": (0.16, 0.0001, -0.5), "z": (0.12, 0, 0)},
    "C": {"y": (0.11, 0.0001, -0.5), "z": (0.08, 0.0002, -0.5)},
    "D": {"y": (0.08, 0.0001, -0.5), "z": (0.06, 0.0015, -0.5)},
    "E": {"y": (0.06, 0.0001, -0.5), "z": (0.03, 0.0003, -1)},
    "F": {"y": (0.04, 0.0001, -0.5), "z": (0.016, 0.0003, -1)},
}


def stability_class_from_wind(wind_speed_ms, is_daytime=True):
    """Rough Pasquill stability estimate from wind speed alone
    (a real implementation would also use solar insolation / cloud cover;
    we use wind speed as the dominant, readily-available proxy)."""
    if wind_speed_ms < 2:
        return "A" if is_daytime else "F"
    elif wind_speed_ms < 3:
        return "B" if is_daytime else "E"
    elif wind_speed_ms < 5:
        return "C" if is_daytime else "D"
    else:
        return "D"


def _sigma(coeffs, x_m):
    a, b, c = coeffs
    return a * x_m / math.sqrt(1 + b * x_m) if b else a * x_m ** (1 + c)


def ground_level_concentration(Q_g_s, wind_speed_ms, stability_class, stack_height_m, distances_m):
    """Return centerline (y=0) ground-level (z=0) concentration in µg/m³
    at each downwind distance in distances_m."""
    coeffs = _BRIGGS_RURAL.get(stability_class, _BRIGGS_RURAL["D"])
    u = max(wind_speed_ms, 0.5)  # avoid divide-by-zero on calm days
    H = stack_height_m
    out = []
    for x in distances_m:
        if x <= 0:
            out.append(0.0)
            continue
        sig_y = max(_sigma(coeffs["y"], x), 0.1)
        sig_z = max(_sigma(coeffs["z"], x), 0.1)
        term = (Q_g_s / (2 * math.pi * u * sig_y * sig_z)) * math.exp(-(H ** 2) / (2 * sig_z ** 2))
        out.append(round(term * 1_000_000, 2))  # g/m^3 -> µg/m^3
    return out


def estimate_emission_rate(industrial_sites, construction_sites, aqi_baseline):
    """Rough proxy for a zone's aggregate emission rate (g/s), derived from
    real land-use counts and current AQI level. This stands in for permit-
    registry emission-factor lookups in a production system."""
    base = 0.4 * industrial_sites + 0.15 * construction_sites
    intensity = max(0.3, aqi_baseline / 150)
    return round(max(0.05, base * intensity), 3)