from flask import Blueprint, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.constants import Role, ReportType
from app.models.review import Review
from app.models.shop import Shop
from app.models.product import Product
from app.models.service import Service
from app.models.report import Report
from app.services import recommendation_service, review_service
from app.controllers.helpers import role_required

review_bp = Blueprint("review", __name__, url_prefix="/review")


@review_bp.route("/submit", methods=["POST"])
@login_required
@role_required(Role.CUSTOMER)
def submit():
    f = request.form
    shop_id = f.get("shop_id")
    product_id = f.get("product_id") or None
    service_id = f.get("service_id") or None
    rating = f.get("rating", type=int)
    text = f.get("review_text", "").strip() or None

    if not rating or rating < 1 or rating > 5:
        flash("Choose a rating between 1 and 5 stars.", "error")
        return redirect(f.get("next") or url_for("customer.dashboard"))

    # Backend-enforced eligibility (spec #5): only a genuinely completed
    # (collected) reservation with this shop/product qualifies — viewing a
    # page is never enough, and this cannot be bypassed by posting the form
    # directly even if the button is hidden client-side.
    reservation = review_service.eligible_reservation(current_user.id, shop_id, product_id=product_id)
    if not reservation:
        flash("Reviews are only available after you've collected a reservation from this "
              "shop" + (" for this product" if product_id else "") + ".", "error")
        return redirect(f.get("next") or url_for("customer.dashboard"))

    if review_service.already_reviewed(current_user.id, shop_id, product_id=product_id):
        flash("You've already reviewed this. Thanks for your feedback!", "error")
        return redirect(f.get("next") or url_for("customer.dashboard"))

    review = Review(user_id=current_user.id, shop_id=shop_id, product_id=product_id,
                     service_id=service_id, rating=rating, review_text=text, verified=True)
    db.session.add(review)
    db.session.commit()
    flash("Thanks for your review!", "success")
    return redirect(f.get("next") or url_for("customer.dashboard"))


@review_bp.route("/recommend", methods=["POST"])
@login_required
@role_required(Role.CUSTOMER)
def recommend():
    f = request.form
    shop = Shop.query.get_or_404(f.get("shop_id"))
    if not review_service.is_eligible(current_user.id, shop.id):
        flash("You can recommend a shop after you've collected a reservation there.", "error")
        return redirect(f.get("next") or url_for("product.shop_profile", shop_id=shop.id))
    recommendation_service.submit_recommendation(current_user, shop, f.get("recommended") == "yes", verified=True)
    flash("Thanks for letting other customers know!", "success")
    return redirect(f.get("next") or url_for("product.shop_profile", shop_id=shop.id))


@review_bp.route("/report", methods=["POST"])
@login_required
def report():
    f = request.form
    report_type = f.get("report_type")
    if report_type not in ReportType.ALL:
        abort(400)
    r = Report(
        reported_by=current_user.id,
        shop_id=f.get("shop_id") or None,
        product_id=f.get("product_id") or None,
        review_id=f.get("review_id") or None,
        report_type=report_type,
        description=f.get("description", "").strip() or None,
    )
    db.session.add(r)
    db.session.commit()
    flash("Thanks — our team will look into this.", "success")
    return redirect(f.get("next") or url_for("customer.dashboard"))
