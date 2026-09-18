from datetime import datetime, timezone

from app.extensions import db
from app.constants import ReservationStatus, PaymentMethod, PaymentStatus

# Pickup/collection hold window once a shopkeeper confirms a reservation
# (spec: "NearCart design ... use a 30-minute reservation hold after
# confirmation"). Centralized here so it's configurable in one place.
RESERVATION_HOLD_MINUTES = 30


def utcnow():
    return datetime.now(timezone.utc)


class Reservation(db.Model):
    __tablename__ = "reservations"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True)
    quantity = db.Column(db.Integer, default=1)
    fulfilment_type = db.Column(db.String(20), nullable=True)  # PICKUP / DELIVERY, set on confirm
    status = db.Column(db.String(20), default=ReservationStatus.PENDING, index=True)
    note = db.Column(db.String(255), nullable=True)
    rejection_reason = db.Column(db.String(255), nullable=True)

    # Price snapshot at the moment of reservation so the digital receipt
    # stays accurate even if the shop later edits the product price.
    unit_price_snapshot = db.Column(db.Float, nullable=True)

    payment_method = db.Column(db.String(20), default=PaymentMethod.PAY_AT_SHOP)
    payment_status = db.Column(db.String(20), default=PaymentStatus.NOT_APPLICABLE)

    # Set once the reservation reaches FULFILLED (doc: digital receipt).
    receipt_number = db.Column(db.String(30), nullable=True, unique=True)

    requested_at = db.Column(db.DateTime, default=utcnow)
    confirmed_at = db.Column(db.DateTime, nullable=True)
    ready_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    # Pickup-countdown deadline. Only meaningful once CONFIRMED — set by
    # reservation_service.confirm() to confirmed_at + RESERVATION_HOLD_MINUTES.
    expires_at = db.Column(db.DateTime, nullable=True)

    customer = db.relationship("User")
    shop = db.relationship("Shop")
    product = db.relationship("Product")
    delivery = db.relationship("Delivery", backref="reservation", uselist=False,
                                cascade="all, delete-orphan")

    def can_transition_to(self, new_status):
        return new_status in ReservationStatus.TRANSITIONS.get(self.status, set())

    @property
    def total_price(self):
        if self.unit_price_snapshot is None:
            return None
        return round(self.unit_price_snapshot * (self.quantity or 1), 2)

    @property
    def seconds_remaining(self):
        """Whole seconds left on the pickup countdown, or None if not running."""
        if self.status not in ("CONFIRMED", "READY") or not self.expires_at:
            return None
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        remaining = (expires_at - utcnow()).total_seconds()
        return max(0, int(remaining))
