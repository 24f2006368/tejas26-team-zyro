from flask import Blueprint, render_template, request, session, current_app
from flask_login import login_required

from app.services import search_service, ai_service
from app.services.location_service import parse_radius_km, SEARCH_RADIUS_OPTIONS_KM

search_bp = Blueprint("search", __name__, url_prefix="/search")


def _location():
    lat = request.args.get("lat", session.get("lat"))
    lon = request.args.get("lon", session.get("lon"))
    try:
        return float(lat), float(lon)
    except (TypeError, ValueError):
        return None, None


def _radius():
    default = current_app.config.get("DEFAULT_SEARCH_RADIUS_KM", 5.0)
    raw = request.args.get("radius", session.get("radius_km", default))
    radius = parse_radius_km(raw, default=default)
    session["radius_km"] = radius
    return radius


@search_bp.route("/")
@login_required
def results():
    raw_query = request.args.get("q", "").strip()
    sort = request.args.get("sort", "relevance")
    lat, lon = _location()
    radius = _radius()

    interpreted = ai_service.interpret_search_query(raw_query) if raw_query else None
    query = interpreted["cleaned_query"] if interpreted else raw_query

    products = search_service.search_products(query, lat=lat, lon=lon, radius_km=radius, sort=sort)
    services = search_service.search_services(query, lat=lat, lon=lon, radius_km=radius)
    shops = search_service.nearby_shops(lat, lon, radius_km=radius, query=query, limit=20)

    radius_extra = {k: v for k, v in {"q": raw_query, "sort": sort, "lat": lat, "lon": lon}.items() if v}

    return render_template(
        "customer/search_results.html", q=raw_query, products=products, services=services,
        shops=shops, sort=sort, lat=lat, lon=lon, radius=radius, interpreted=interpreted,
        radius_options=SEARCH_RADIUS_OPTIONS_KM, radius_extra=radius_extra,
    )
