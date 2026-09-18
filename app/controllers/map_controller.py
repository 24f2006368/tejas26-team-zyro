"""JSON API endpoints — kept API-friendly per doc #62/#92 so a future
React/mobile frontend can reuse the same backend without rewriting logic."""
from flask import Blueprint, jsonify, request, session
from flask_login import login_required

from app.services import search_service, map_service
from app.services.location_service import format_distance

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _shop_json(shop):
    return {
        "id": shop.id,
        "name": shop.name,
        "category": shop.category.name if shop.category else None,
        "category_type": shop.category.type if shop.category else None,
        "latitude": shop.latitude,
        "longitude": shop.longitude,
        "distance_km": getattr(shop, "distance_km", None),
        "distance_label": format_distance(getattr(shop, "distance_km", None)),
        "rating": shop.rating_average,
        "review_count": shop.review_count,
        "recommendation_percentage": shop.recommendation_percentage,
        "verified": shop.is_verified,
        "opening_time": shop.opening_time,
        "closing_time": shop.closing_time,
        "url": f"/shop/{shop.id}",
    }


@api_bp.route("/shops/nearby")
@login_required
def shops_nearby():
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    radius = request.args.get("radius", 5.0, type=float)
    category_type = request.args.get("category")
    q = request.args.get("q")

    if lat is None or lon is None:
        return jsonify({"error": "lat and lon are required"}), 400

    shops = search_service.nearby_shops(lat, lon, radius_km=radius, category_type=category_type, query=q)
    return jsonify({
        "user_location": {"lat": lat, "lon": lon},
        "map": map_service.map_config(),
        "shops": [_shop_json(s) for s in shops],
    })


@api_bp.route("/shops/<int:shop_id>/route")
@login_required
def shop_route(shop_id):
    from app.models.shop import Shop
    shop = Shop.query.get_or_404(shop_id)
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    mode = request.args.get("mode", "walking")
    if lat is None or lon is None:
        return jsonify({"error": "lat and lon are required"}), 400
    preview = map_service.route_preview((lat, lon), (shop.latitude, shop.longitude), mode=mode)
    return jsonify(preview or {"error": "unable to compute route"})


@api_bp.route("/search")
@login_required
def search():
    q = request.args.get("q", "")
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    radius = request.args.get("radius", 5.0, type=float)
    products = search_service.search_products(q, lat=lat, lon=lon, radius_km=radius)
    return jsonify({"products": [
        {"id": p.id, "name": p.name, "shop": p.shop.name, "price": p.discounted_price,
         "distance_km": getattr(p, "distance_km", None)} for p in products
    ]})
