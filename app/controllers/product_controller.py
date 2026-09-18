from flask import Blueprint, render_template, request, session
from flask_login import login_required, current_user

from app.constants import ReviewStatus
from app.models.shop import Shop
from app.models.product import Product
from app.models.service import Service
from app.models.review import Review
from app.models.notification import SavedItem
from app.services import search_service, trending_service, review_service
from app.services.location_service import haversine_km

product_bp = Blueprint("product", __name__, url_prefix="")


def _location():
    lat = request.args.get("lat", session.get("lat"))
    lon = request.args.get("lon", session.get("lon"))
    try:
        return float(lat), float(lon)
    except (TypeError, ValueError):
        return None, None


@product_bp.route("/shop/<int:shop_id>")
@login_required
def shop_profile(shop_id):
    shop = Shop.query.get_or_404(shop_id)
    lat, lon = _location()
    distance = haversine_km(lat, lon, shop.latitude, shop.longitude) if lat else None

    products = shop.products.filter_by(status="ACTIVE").all()
    services = shop.services.all()
    offerings = shop.offerings.all()
    shop_reviews = shop.reviews.filter_by(
        product_id=None, service_id=None, status=ReviewStatus.ACTIVE
    ).order_by(Review.created_at.desc()).all()

    is_saved = SavedItem.query.filter_by(user_id=current_user.id, item_type="SHOP",
                                          shop_id=shop.id).first() is not None

    trending_service.log_event(shop.id, "VIEW")

    can_review = review_service.is_eligible(current_user.id, shop.id)
    already_reviewed = review_service.already_reviewed(current_user.id, shop.id)

    return render_template(
        "shop/profile.html", shop=shop, products=products, services=services,
        offerings=offerings, shop_reviews=shop_reviews, distance=distance, is_saved=is_saved,
        can_review=can_review, already_reviewed=already_reviewed,
    )


@product_bp.route("/product/<int:product_id>")
@login_required
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    lat, lon = _location()
    distance = haversine_km(lat, lon, product.shop.latitude, product.shop.longitude) if lat else None
    reviews = product.reviews.filter_by(status=ReviewStatus.ACTIVE).order_by(
        Review.created_at.desc()).all()
    alternatives = search_service.compare_product(product.name, lat=lat, lon=lon, radius_km=10.0)
    alternatives = [p for p in alternatives if p.id != product.id][:5]

    is_saved = SavedItem.query.filter_by(user_id=current_user.id, item_type="PRODUCT",
                                          product_id=product.id).first() is not None

    trending_service.log_event(product.shop_id, "VIEW", product_id=product.id)

    can_review = review_service.is_eligible(current_user.id, product.shop_id, product_id=product.id)
    already_reviewed = review_service.already_reviewed(current_user.id, product.shop_id, product_id=product.id)

    return render_template(
        "product/detail.html", product=product, distance=distance, reviews=reviews,
        alternatives=alternatives, is_saved=is_saved,
        can_review=can_review, already_reviewed=already_reviewed,
    )


@product_bp.route("/service/<int:service_id>")
@login_required
def service_detail(service_id):
    service = Service.query.get_or_404(service_id)
    lat, lon = _location()
    distance = haversine_km(lat, lon, service.shop.latitude, service.shop.longitude) if lat else None
    return render_template("product/service_detail.html", service=service, distance=distance)


@product_bp.route("/compare")
@login_required
def compare():
    name = request.args.get("q", "").strip()
    lat, lon = _location()
    radius = float(request.args.get("radius", 10.0))
    results = search_service.compare_product(name, lat=lat, lon=lon, radius_km=radius) if name else []
    sort = request.args.get("sort", "price_low")
    if sort == "nearest":
        results.sort(key=lambda p: (p.distance_km if p.distance_km is not None else 1e9))
    elif sort == "rating":
        results.sort(key=lambda p: -(p.rating_average or 0))
    return render_template("product/compare.html", q=name, results=results, sort=sort)
