"""Map-provider-specific logic lives here only (doc #18/#71). The prototype
uses Leaflet + OpenStreetMap tiles (no paid API key). To move to Google Maps
or Mapbox later, change MAP_PROVIDER in config and the values this module
returns — routes/templates never talk to the provider directly."""
from flask import current_app


def map_config():
    return {
        "provider": current_app.config.get("MAP_PROVIDER", "leaflet"),
        "api_key": current_app.config.get("MAP_API_KEY", ""),
        "tile_url": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        "attribution": "&copy; OpenStreetMap contributors",
    }


def route_preview(origin, destination, mode="walking"):
    """Straight-line ETA estimate used by the prototype's route preview card.
    A real deployment would call the provider's directions API here."""
    from app.services.location_service import haversine_km
    distance_km = haversine_km(origin[0], origin[1], destination[0], destination[1])
    if distance_km is None:
        return None
    speeds_kmh = {"walking": 4.5, "bike": 15, "car": 25}
    speed = speeds_kmh.get(mode, 4.5)
    eta_minutes = max(1, round((distance_km / speed) * 60))
    return {"distance_km": round(distance_km, 2), "eta_minutes": eta_minutes, "mode": mode}
