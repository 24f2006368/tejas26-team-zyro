"""Reservation state-machine transitions (doc #23/#30/#64). Every mutation
goes through here so a client can never push an arbitrary status."""
from datetime import datetime, timezone, timedelta

from app.extensions import db
from app.constants import ReservationStatus, NotificationType, PaymentMethod, PaymentStatus
from app.models.reservation import Reservation, RESERVATION_HOLD_MINUTES
from app.services import recommendation_service


class InvalidTransition(Exception):
    pass


def create_reservation(customer, shop, product=None, quantity=1, note=None, payment_method=None):
    if payment_method not in PaymentMethod.ALL:
        payment_method = PaymentMethod.PAY_AT_SHOP

    reservation = Reservation(
        customer_id=customer.id,
        shop_id=shop.id,
        product_id=product.id if product else None,
        quantity=quantity,
        note=note,
        status=ReservationStatus.PENDING,
        unit_price_snapshot=product.discounted_price if product else None,
        payment_method=payment_method,
        # The demo online flow "pays" immediately on request; pay-at-shop
        # payment status stays PENDING until the customer actually collects.
        payment_status=(
            PaymentStatus.PAID_DEMO if payment_method == PaymentMethod.PAY_ONLINE_DEMO
            else PaymentStatus.PENDING
        ),
        # A shop that never responds to a pending request shouldn't sit
        # forever — pending requests auto-expire after 24h. The real,
        # customer-visible pickup countdown only starts once confirmed
        # (see confirm() below), overwriting this value.
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db.session.add(reservation)
    db.session.commit()

    from app.services.notification_service import notify
    notify(shop.owner_id, NotificationType.RESERVATION_REQUESTED,
           "New reservation request",
           f"{customer.name} requested {product.name if product else 'an item'}",
           link=f"/shopkeeper/reservations")
    return reservation


def _transition(reservation, new_status):
    if not reservation.can_transition_to(new_status):
        raise InvalidTransition(f"Cannot move reservation from {reservation.status} to {new_status}")
    reservation.status = new_status


def sync_expiry(reservation):
    """Lazily flips an overdue CONFIRMED/READY reservation to EXPIRED.

    There is no background worker in this prototype, so expiry is evaluated
    on read (whenever a reservation is fetched for display) — the backend
    expires_at timestamp remains the single source of truth; the frontend
    countdown never decides expiry itself."""
    if reservation.status in (ReservationStatus.CONFIRMED, ReservationStatus.READY):
        if reservation.seconds_remaining == 0:
            reservation.status = ReservationStatus.EXPIRED
            db.session.commit()
            from app.services.notification_service import notify
            notify(reservation.customer_id, NotificationType.RESERVATION_REJECTED,
                   "Reservation expired",
                   f"Your reservation hold at {reservation.shop.name} has ended.",
                   link="/customer/reservations")
    return reservation


def confirm(reservation):
    _transition(reservation, ReservationStatus.CONFIRMED)
    now = datetime.now(timezone.utc)
    reservation.confirmed_at = now
    reservation.expires_at = now + timedelta(minutes=RESERVATION_HOLD_MINUTES)
    db.session.commit()
    from app.services.notification_service import notify
    notify(reservation.customer_id, NotificationType.RESERVATION_CONFIRMED,
           "Reservation confirmed",
           f"Your reservation at {reservation.shop.name} was confirmed. "
           f"Pick it up within {RESERVATION_HOLD_MINUTES} minutes.",
           link=f"/customer/reservations")
    return reservation


def reject(reservation, reason=None):
    _transition(reservation, ReservationStatus.REJECTED)
    reservation.rejection_reason = reason
    db.session.commit()
    from app.services.notification_service import notify
    notify(reservation.customer_id, NotificationType.RESERVATION_REJECTED,
           "Reservation could not be confirmed",
           f"{reservation.shop.name} could not confirm this item.",
           link=f"/customer/reservations")
    return reservation


def mark_ready(reservation):
    _transition(reservation, ReservationStatus.READY)
    reservation.ready_at = datetime.now(timezone.utc)
    db.session.commit()
    from app.services.notification_service import notify
    notify(reservation.customer_id, NotificationType.ORDER_READY,
           "Your order is ready",
           f"Your item at {reservation.shop.name} is ready.",
           link=f"/customer/reservations")
    return reservation


def _generate_receipt_number(reservation):
    return f"NC-{reservation.id:06d}"


def complete(reservation):
    _transition(reservation, ReservationStatus.FULFILLED)
    reservation.completed_at = datetime.now(timezone.utc)
    reservation.receipt_number = _generate_receipt_number(reservation)
    if reservation.payment_method == PaymentMethod.PAY_AT_SHOP:
        reservation.payment_status = PaymentStatus.PAID_DEMO
    db.session.commit()
    recommendation_service.prompt_eligible(reservation)
    return reservation


def cancel(reservation):
    _transition(reservation, ReservationStatus.CANCELLED)
    db.session.commit()
    return reservation
