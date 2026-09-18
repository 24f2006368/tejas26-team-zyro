"""Admin demand/supply reporting (improvement spec #11/#12): aggregates
*real* database data only — no invented numbers — into rows the admin
overview can preview, and PDF/Excel exports can render from the exact same
query. Demand is derived from ActivityEvent (VIEW/RESERVE logs) and actual
Reservation counts; supply is derived from the Product catalogue itself."""
from datetime import datetime, timezone

from sqlalchemy import func

from app.extensions import db
from app.constants import VerificationStatus
from app.models.product import Product
from app.models.shop import Shop
from app.models.category import Category
from app.models.reservation import Reservation
from app.models.notification import ActivityEvent


def _date_bounds(start=None, end=None):
    if start:
        start = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if end:
        end = datetime.strptime(end, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
    return start, end


def demand_report(start=None, end=None):
    """Product, Category, Shop, Views, Reserve requests, Completed
    reservations, Price, Availability — one row per active, approved
    product, ranked by real reservation-request activity."""
    start_dt, end_dt = _date_bounds(start, end)

    views_q = db.session.query(
        ActivityEvent.product_id, func.count(ActivityEvent.id)
    ).filter(ActivityEvent.event_type == "VIEW", ActivityEvent.product_id.isnot(None))
    reserves_q = db.session.query(
        ActivityEvent.product_id, func.count(ActivityEvent.id)
    ).filter(ActivityEvent.event_type == "RESERVE", ActivityEvent.product_id.isnot(None))
    completed_q = db.session.query(
        Reservation.product_id, func.count(Reservation.id)
    ).filter(Reservation.status == "FULFILLED", Reservation.product_id.isnot(None))

    if start_dt:
        views_q = views_q.filter(ActivityEvent.created_at >= start_dt)
        reserves_q = reserves_q.filter(ActivityEvent.created_at >= start_dt)
        completed_q = completed_q.filter(Reservation.completed_at >= start_dt)
    if end_dt:
        views_q = views_q.filter(ActivityEvent.created_at <= end_dt)
        reserves_q = reserves_q.filter(ActivityEvent.created_at <= end_dt)
        completed_q = completed_q.filter(Reservation.completed_at <= end_dt)

    views = dict(views_q.group_by(ActivityEvent.product_id).all())
    reserves = dict(reserves_q.group_by(ActivityEvent.product_id).all())
    completed = dict(completed_q.group_by(Reservation.product_id).all())

    products = (
        Product.query.join(Shop, Product.shop_id == Shop.id)
        .filter(Shop.verification_status == VerificationStatus.APPROVED)
        .filter(Product.status == "ACTIVE")
        .all()
    )

    rows = []
    for p in products:
        view_count = views.get(p.id, 0)
        reserve_count = reserves.get(p.id, 0)
        completed_count = completed.get(p.id, 0)
        if view_count == 0 and reserve_count == 0 and completed_count == 0:
            continue  # no real demand signal at all — skip rather than pad with zeros
        rows.append({
            "product": p.name,
            "category": p.category.name if p.category else "—",
            "shop": p.shop.name,
            "views": view_count,
            "reserve_requests": reserve_count,
            "completed_reservations": completed_count,
            "price": p.discounted_price,
            "availability": p.availability_status,
        })
    rows.sort(key=lambda r: (r["reserve_requests"], r["views"]), reverse=True)
    return rows


def supply_report(start=None, end=None):
    """Product, Category, Shop, Price, Availability, Rating, Reviews,
    Last Updated — one row per active, approved product. `start`/`end`
    filter to products whose price was last updated in that window."""
    start_dt, end_dt = _date_bounds(start, end)

    q = (
        Product.query.join(Shop, Product.shop_id == Shop.id)
        .filter(Shop.verification_status == VerificationStatus.APPROVED)
        .filter(Product.status == "ACTIVE")
    )
    if start_dt:
        q = q.filter(Product.price_updated_at >= start_dt)
    if end_dt:
        q = q.filter(Product.price_updated_at <= end_dt)

    rows = []
    for p in q.all():
        rows.append({
            "product": p.name,
            "category": p.category.name if p.category else "—",
            "shop": p.shop.name,
            "price": p.discounted_price,
            "availability": p.availability_status,
            "rating": p.rating_average,
            "reviews": p.review_count,
            "last_updated": p.price_updated_at,
        })
    rows.sort(key=lambda r: r["shop"])
    return rows
