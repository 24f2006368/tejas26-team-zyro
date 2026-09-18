from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_required, current_user

from app.extensions import db
from app.constants import Role, VerificationStatus, SavedItemType, ReservationStatus
from app.models.shop import Shop
from app.models.product import Product
from app.models.category import Category
from app.models.notification import SavedItem, Notification
from app.models.reservation import Reservation
from app.services import search_service, trending_service, notification_service, reservation_service
from app.services.location_service import parse_radius_km, SEARCH_RADIUS_OPTIONS_KM
from app.controllers.helpers import role_required

customer_bp = Blueprint("customer", __name__, url_prefix="/customer")


def _user_location():
    lat = request.args.get("lat", session.get("lat"))
    lon = request.args.get("lon", session.get("lon"))
    if request.args.get("lat"):
        session["lat"] = request.args.get("lat")
        session["lon"] = request.args.get("lon")
    try:
        return float(lat), float(lon)
    except (TypeError, ValueError):
        return None, None


def _search_radius():
    default = current_app.config.get("DEFAULT_SEARCH_RADIUS_KM", 5.0)
    raw = request.args.get("radius", session.get("radius_km", default))
    radius = parse_radius_km(raw, default=default)
    session["radius_km"] = radius
    return radius


@customer_bp.route("/")
@login_required
@role_required(Role.CUSTOMER)
def dashboard():
    lat, lon = _user_location()
    radius = _search_radius()
    nearby = search_service.nearby_shops(lat, lon, radius_km=radius, limit=12) if lat else []
    categories = Category.query.filter(Category.parent_id.is_(None)).limit(8).all()
    trending = trending_service.trending_shops(limit=6) or Shop.query.filter_by(
        verification_status=VerificationStatus.APPROVED).limit(6).all()
    discover = Shop.query.filter_by(verification_status=VerificationStatus.APPROVED).order_by(
        Shop.created_at.desc()).limit(6).all()
    saved = SavedItem.query.filter_by(user_id=current_user.id).order_by(
        SavedItem.created_at.desc()).limit(6).all()

    radius_extra = {"lat": lat, "lon": lon} if lat is not None else {}

    return render_template(
        "customer/dashboard.html", nearby=nearby, categories=categories,
        trending=trending, discover=discover, saved=saved, has_location=lat is not None,
        radius=radius, radius_options=SEARCH_RADIUS_OPTIONS_KM, lat=lat, lon=lon,
        radius_extra=radius_extra,
    )


@customer_bp.route("/explore")
@login_required
@role_required(Role.CUSTOMER)
def explore():
    lat, lon = _user_location()
    category_type = request.args.get("category")
    q = request.args.get("q", "").strip()
    radius = _search_radius()

    shops = search_service.nearby_shops(lat, lon, radius_km=radius, category_type=category_type, query=q)
    radius_extra = {k: v for k, v in {"lat": lat, "lon": lon, "category": category_type, "q": q}.items() if v}
    return render_template("customer/explore.html", shops=shops, lat=lat, lon=lon,
                            category=category_type, q=q, radius=radius,
                            radius_options=SEARCH_RADIUS_OPTIONS_KM, radius_extra=radius_extra)


@customer_bp.route("/set-location", methods=["POST"])
@login_required
def set_location():
    lat = request.form.get("lat")
    lon = request.form.get("lon")
    if lat and lon:
        session["lat"] = lat
        session["lon"] = lon
    return redirect(request.form.get("next") or url_for("customer.dashboard"))


@customer_bp.route("/saved")
@login_required
@role_required(Role.CUSTOMER)
def saved():
    items = SavedItem.query.filter_by(user_id=current_user.id).order_by(
        SavedItem.created_at.desc()).all()
    return render_template("customer/saved.html", items=items)


@customer_bp.route("/save", methods=["POST"])
@login_required
@role_required(Role.CUSTOMER)
def save_item():
    item_type = request.form.get("item_type")
    shop_id = request.form.get("shop_id")
    product_id = request.form.get("product_id")

    existing = SavedItem.query.filter_by(
        user_id=current_user.id, item_type=item_type,
        shop_id=shop_id or None, product_id=product_id or None,
    ).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        flash("Removed from saved.", "success")
    else:
        db.session.add(SavedItem(user_id=current_user.id, item_type=item_type,
                                  shop_id=shop_id or None, product_id=product_id or None))
        db.session.commit()
        if shop_id:
            trending_service.log_event(int(shop_id), "SAVE")
        flash("Saved.", "success")
    return redirect(request.form.get("next") or url_for("customer.saved"))


@customer_bp.route("/reservations")
@login_required
@role_required(Role.CUSTOMER)
def reservations():
    items = Reservation.query.filter_by(customer_id=current_user.id).order_by(
        Reservation.requested_at.desc()).all()
    for item in items:
        reservation_service.sync_expiry(item)
    return render_template("customer/reservations.html", reservations=items)


@customer_bp.route("/notifications")
@login_required
def notifications():
    items = Notification.query.filter_by(user_id=current_user.id).order_by(
        Notification.created_at.desc()).limit(50).all()
    notification_service.mark_all_read(current_user.id)
    return render_template("customer/notifications.html", notifications=items)


@customer_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        current_user.name = request.form.get("name", current_user.name).strip()
        current_user.address = request.form.get("address", current_user.address)
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("customer.profile"))
    return render_template("customer/profile.html")
