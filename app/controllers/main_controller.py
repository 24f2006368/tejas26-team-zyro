import os

from flask import Blueprint, current_app, render_template, send_from_directory
from flask_login import current_user
from sqlalchemy import func

from app.models.shop import Shop
from app.models.category import Category
from app.constants import VerificationStatus, CategoryType

main_bp = Blueprint("main", __name__, url_prefix="")

CATEGORY_ICONS = {
    "electronics": "bolt",
    "grocery": "basket",
    "clothing": "shirt",
    "hardware": "wrench",
    "stationery": "pencil",
    "mechanic": "wrench",
    "mobile-repair": "smartphone",
    "tailor": "scissors",
    "restaurants": "utensils",
    "street-food": "bowl",
    "bakeries": "cake",
    "local-specialties": "star",
    "other": "dots",
}


@main_bp.route("/")
def home():
    if current_user.is_authenticated:
        from app.constants import Role
        if current_user.role == Role.SHOPKEEPER:
            from flask import redirect, url_for
            return redirect(url_for("shopkeeper.home"))
        if current_user.role == Role.ADMIN:
            from flask import redirect, url_for
            return redirect(url_for("admin.overview"))

    shop_count = Shop.query.filter_by(verification_status=VerificationStatus.APPROVED).count()

    category_counts = dict(
        db_session_query_category_counts()
    )
    categories = (
        Category.query.filter(Category.parent_id.is_(None))
        .filter(Category.type != CategoryType.OTHER)
        .order_by(Category.name)
        .limit(8)
        .all()
    )
    for cat in categories:
        cat.nearby_count = category_counts.get(cat.id, 0)

    featured_shops = (
        Shop.query.filter_by(verification_status=VerificationStatus.APPROVED)
        .order_by(Shop.created_at.desc())
        .limit(3)
        .all()
    )

    return render_template(
        "home.html",
        shop_count=shop_count,
        categories=categories,
        featured_shops=featured_shops,
        category_icons=CATEGORY_ICONS,
    )


def db_session_query_category_counts():
    from app.extensions import db

    rows = (
        db.session.query(Shop.category_id, func.count(Shop.id))
        .filter(Shop.verification_status == VerificationStatus.APPROVED)
        .group_by(Shop.category_id)
        .all()
    )
    return rows


@main_bp.route("/about")
def about():
    return render_template("about.html")


@main_bp.route("/download-source")
def download_source():
    downloads_dir = os.path.join(current_app.static_folder, "downloads")
    return send_from_directory(
        downloads_dir, "nearcart-source.zip",
        as_attachment=True, download_name="nearcart-source.zip",
    )
