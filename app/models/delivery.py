from datetime import datetime, timezone

from app.extensions import db
from app.constants import DeliveryStatus

def utcnow():
    return datetime.now(timezone.utc)


class Delivery(db.Model):
    __tablename__ = "deliveries"

    id = db.Column(db.Integer, primary_key=True)
    reservation_id = db.Column(db.Integer, db.ForeignKey("reservations.id"),
                                nullable=False, unique=True)
    partner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    pickup_address = db.Column(db.String(255), nullable=True)
    drop_address = db.Column(db.String(255), nullable=True)
    delivery_fee = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(30), default=DeliveryStatus.REQUESTED, index=True)

    created_at = db.Column(db.DateTime, default=utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    partner = db.relationship("User")

    def can_transition_to(self, new_status):
        return new_status in DeliveryStatus.TRANSITIONS.get(self.status, set())
