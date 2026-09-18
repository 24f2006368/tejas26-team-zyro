from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.constants import Role, ReservationStatus, FulfilmentType
from app.models.shop import Shop
from app.models.product import Product
from app.models.reservation import Reservation
from app.services import reservation_service, delivery_service, trending_service
from app.controllers.helpers import role_required

reservation_bp = Blueprint("reservation", __name__, url_prefix="/reservation")


@reservation_bp.route("/create", methods=["POST"])
@login_required
@role_required(Role.CUSTOMER)
def create():
    f = request.form
    shop = Shop.query.get_or_404(f.get("shop_id"))
    product = Product.query.get(f["product_id"]) if f.get("product_id") else None

    reservation = reservation_service.create_reservation(
        current_user, shop, product=product,
        quantity=f.get("quantity", 1, type=int), note=f.get("note", "").strip() or None,
        payment_method=f.get("payment_method"),
    )
    trending_service.log_event(shop.id, "RESERVE", product_id=product.id if product else None)
    flash("Reservation requested. The shop will confirm shortly.", "success")
    return redirect(url_for("reservation.detail", reservation_id=reservation.id))


@reservation_bp.route("/<int:reservation_id>")
@login_required
def detail(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    if not current_user.is_admin and reservation.customer_id != current_user.id:
        abort(403)
    reservation_service.sync_expiry(reservation)
    return render_template("customer/reservation_detail.html", reservation=reservation)


@reservation_bp.route("/<int:reservation_id>/receipt")
@login_required
def receipt(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    if not current_user.is_admin and reservation.customer_id != current_user.id:
        abort(403)
    if reservation.status != ReservationStatus.FULFILLED:
        flash("The digital receipt is available once this reservation is collected.", "error")
        return redirect(url_for("reservation.detail", reservation_id=reservation.id))
    return render_template("customer/receipt.html", reservation=reservation)


@reservation_bp.route("/<int:reservation_id>/fulfilment", methods=["POST"])
@login_required
@role_required(Role.CUSTOMER)
def choose_fulfilment(reservation_id):
    """Doc #31/#32/#81: pickup is free/default; delivery is optional and
    only offered when the shop has enabled it."""
    reservation = Reservation.query.get_or_404(reservation_id)
    if reservation.customer_id != current_user.id:
        abort(403)
    if reservation.status != ReservationStatus.CONFIRMED and reservation.status != ReservationStatus.READY:
        flash("This reservation is not ready for fulfilment choice yet.", "error")
        return redirect(url_for("reservation.detail", reservation_id=reservation.id))

    choice = request.form.get("choice")
    reservation.fulfilment_type = choice
    db.session.commit()

    if choice == FulfilmentType.DELIVERY:
        if not reservation.shop.delivery_enabled:
            flash("This shop does not support delivery yet.", "error")
            return redirect(url_for("reservation.detail", reservation_id=reservation.id))
        drop_address = request.form.get("drop_address") or current_user.address or "Customer address"
        delivery_service.request_delivery(reservation, drop_address)
        flash("Delivery requested. A partner will be assigned shortly.", "success")
    else:
        flash("Pickup selected. Visit the shop once it's marked ready.", "success")

    return redirect(url_for("reservation.detail", reservation_id=reservation.id))


@reservation_bp.route("/<int:reservation_id>/collect", methods=["POST"])
@login_required
@role_required(Role.CUSTOMER)
def mark_collected(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    if reservation.customer_id != current_user.id:
        abort(403)
    try:
        reservation_service.complete(reservation)
        flash("Marked as collected. Enjoy!", "success")
    except reservation_service.InvalidTransition as e:
        flash(str(e), "error")
    return redirect(url_for("reservation.detail", reservation_id=reservation.id))


@reservation_bp.route("/<int:reservation_id>/cancel", methods=["POST"])
@login_required
@role_required(Role.CUSTOMER)
def cancel(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    if reservation.customer_id != current_user.id:
        abort(403)
    try:
        reservation_service.cancel(reservation)
        flash("Reservation cancelled.", "success")
    except reservation_service.InvalidTransition as e:
        flash(str(e), "error")
    return redirect(url_for("customer.reservations"))
