"""Delivery request + simple nearest-available-partner matching (doc #33/#75).
MVP matching: any active delivery_partner user is a candidate; a real system
would filter by current location/availability."""
from app.extensions import db
from app.constants import DeliveryStatus, Role, NotificationType
from app.models.delivery import Delivery
from app.models.user import User


def request_delivery(reservation, drop_address, base_fee=25.0):
    delivery = Delivery(
        reservation_id=reservation.id,
        pickup_address=reservation.shop.address,
        drop_address=drop_address,
        delivery_fee=base_fee,
        status=DeliveryStatus.REQUESTED,
    )
    db.session.add(delivery)
    db.session.commit()
    _auto_assign(delivery)
    return delivery


def _auto_assign(delivery):
    partner = User.query.filter_by(role=Role.DELIVERY_PARTNER, is_active_account=True).first()
    if partner:
        delivery.partner_id = partner.id
        delivery.status = DeliveryStatus.ASSIGNED
        db.session.commit()
        from app.services.notification_service import notify
        notify(partner.id, NotificationType.DELIVERY_ASSIGNED,
               "New delivery request", "A new delivery request was assigned to you.")


def _transition(delivery, new_status):
    if not delivery.can_transition_to(new_status):
        raise ValueError(f"Cannot move delivery from {delivery.status} to {new_status}")
    delivery.status = new_status


def advance(delivery, new_status):
    from datetime import datetime, timezone
    _transition(delivery, new_status)
    if new_status == DeliveryStatus.DELIVERED:
        delivery.completed_at = datetime.now(timezone.utc)
        from app.services import reservation_service
        reservation_service.complete(delivery.reservation)
        from app.services.notification_service import notify
        notify(delivery.reservation.customer_id, NotificationType.DELIVERY_COMPLETED,
               "Delivered", "Your order has been delivered.")
    db.session.commit()
    return delivery
