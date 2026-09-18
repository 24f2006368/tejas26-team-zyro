"""Delivery partner role is supported at the data/model layer with a
minimal operational dashboard, per doc #33/#62's "limited first phase"
scope — the full dedicated partner app is a later phase."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from app.constants import Role, DeliveryStatus
from app.models.delivery import Delivery
from app.services import delivery_service
from app.controllers.helpers import role_required

delivery_bp = Blueprint("delivery", __name__, url_prefix="/delivery")


@delivery_bp.route("/")
@login_required
@role_required(Role.DELIVERY_PARTNER)
def home():
    assigned = Delivery.query.filter_by(partner_id=current_user.id).filter(
        Delivery.status.notin_([DeliveryStatus.DELIVERED, DeliveryStatus.CANCELLED])
    ).order_by(Delivery.created_at.desc()).all()
    completed = Delivery.query.filter_by(partner_id=current_user.id, status=DeliveryStatus.DELIVERED
                                          ).order_by(Delivery.completed_at.desc()).limit(10).all()
    return render_template("customer/delivery_home.html", assigned=assigned, completed=completed)


@delivery_bp.route("/<int:delivery_id>/advance", methods=["POST"])
@login_required
@role_required(Role.DELIVERY_PARTNER)
def advance(delivery_id):
    delivery = Delivery.query.get_or_404(delivery_id)
    if delivery.partner_id != current_user.id:
        abort(403)
    next_status = request.form.get("status")
    try:
        delivery_service.advance(delivery, next_status)
        flash("Delivery status updated.", "success")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("delivery.home"))
