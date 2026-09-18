from datetime import datetime, timezone

from app.extensions import db

def utcnow():
    return datetime.now(timezone.utc)


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    type = db.Column(db.String(40), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.String(255), nullable=True)
    link = db.Column(db.String(255), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utcnow)


class SavedItem(db.Model):
    __tablename__ = "saved_items"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    item_type = db.Column(db.String(20), nullable=False)  # SHOP / PRODUCT / SERVICE
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id"), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    shop = db.relationship("Shop")
    product = db.relationship("Product")
    service = db.relationship("Service")


class ActivityEvent(db.Model):
    """Raw signal log used by the trending service (doc #49/#75)."""
    __tablename__ = "activity_events"

    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True)
    event_type = db.Column(db.String(30), nullable=False)  # VIEW / SEARCH / SAVE / NAVIGATE / RESERVE
    created_at = db.Column(db.DateTime, default=utcnow, index=True)