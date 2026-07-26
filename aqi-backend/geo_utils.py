"""
Geospatial math utilities -- the missing link that lets us connect real
wind direction to real, specific nearby sources (answering "why is the air
bad HERE, RIGHT NOW" instead of just "this zone is statistically ~20%
construction-type").
"""
import math


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two points, in kilometres."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def bearing_deg(lat1, lon1, lat2, lon2):
    """Initial compass bearing (0-360, 0=North) from point 1 to point 2."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlambda = math.radians(lon2 - lon1)
    x = math.sin(dlambda) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlambda)
    theta = math.atan2(x, y)
    return (math.degrees(theta) + 360) % 360


def angular_diff(a, b):
    """Smallest absolute difference between two compass bearings (0-180)."""
    d = abs(a - b) % 360
    return min(d, 360 - d)


_COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def compass_label(deg):
    idx = round(deg / 22.5) % 16
    return _COMPASS[idx]


def bbox_from_point(lat, lon, radius_m):
    """A simple bounding box around a point, sized in metres. Used to ask
    Overpass a much cheaper indexed range query (south, west, north, east)
    instead of an 'around' filter, which forces the server to compute
    exact geometric distance for every candidate feature -- genuinely
    expensive server-side, not just slow over the network. We still
    enforce the true circular radius ourselves afterward with
    haversine_km(), so accuracy doesn't suffer, only Overpass's workload
    does."""
    deg_lat = radius_m / 111_320.0  # metres per degree latitude, ~constant
    deg_lon = radius_m / (111_320.0 * math.cos(math.radians(lat)) or 1e-9)
    return (lat - deg_lat, lon - deg_lon, lat + deg_lat, lon + deg_lon)  # south, west, north, east


def is_upwind(wind_from_deg, bearing_zone_to_source_deg, tolerance_deg=50):
    """A source is 'upwind' of a zone -- i.e. currently blowing its
    pollution toward the zone -- if the wind is blowing FROM roughly the
    same compass direction the source sits in, relative to the zone.
    wind_from_deg follows meteorological convention (the direction the
    wind is blowing FROM, e.g. 90 = wind from the east)."""
    return angular_diff(wind_from_deg, bearing_zone_to_source_deg) <= tolerance_deg