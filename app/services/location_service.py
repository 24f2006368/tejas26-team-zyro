"""Distance / nearby math. Kept isolated so a future PostGIS ST_DWithin swap
only touches this file (doc #61, #71)."""
import math

#: Options offered by the customer-facing "Search Radius" control (spec #2).
#: A single source of truth so the dashboard, explore map and search results
#: page all validate/offer the exact same radii.
SEARCH_RADIUS_OPTIONS_KM = [0.5, 1, 2, 5, 10, 25, 50]


def parse_radius_km(raw, default=5.0):
    """Coerces a raw (querystring/session) radius value to one of the
    supported options, falling back to `default` for anything invalid —
    this is the single gate a client-supplied radius passes through before
    it ever reaches a search query."""
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return default
    return value if value in SEARCH_RADIUS_OPTIONS_KM else default


def format_radius(km):
    if km < 1:
        return f"{int(round(km * 1000))} m"
    return f"{km:g} km"


def haversine_km(lat1, lon1, lat2, lon2):
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (math.sin(d_phi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def bounding_box(lat, lon, radius_km):
    """Cheap pre-filter box so the DB query can use the lat/lon indexes
    before we compute exact haversine distance in Python."""
    lat_delta = radius_km / 111.0
    lon_delta = radius_km / (111.0 * max(math.cos(math.radians(lat)), 0.1))
    return (lat - lat_delta, lat + lat_delta, lon - lon_delta, lon + lon_delta)


def format_distance(km):
    if km is None:
        return ""
    if km < 1:
        return f"{int(round(km * 1000))} m"
    return f"{km:.1f} km"
