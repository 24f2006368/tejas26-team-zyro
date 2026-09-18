from datetime import datetime, timezone

from app.extensions import db
from app.constants import ReservationStatus

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

    requested_at = db.Column(db.DateTime, default=utcnow)
    confirmed_at = db.Column(db.DateTime, nullable=True)
    ready_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)

    customer = db.relationship("User")
    shop = db.relationship("Shop")
    product = db.relationship("Product")
    delivery = db.relationship("Delivery", backref="reservation", uselist=False,
                                cascade="all, delete-orphan")

    def can_transition_to(self, new_status):
        return new_status in ReservationStatus.TRANSITIONS.get(self.status, set())