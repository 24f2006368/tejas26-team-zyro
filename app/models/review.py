from datetime import datetime, timezone

from app.extensions import db
from app.constants import ReviewStatus

def utcnow():
    return datetime.now(timezone.utc)


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id"), nullable=True, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True, index=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=True, index=True)

    rating = db.Column(db.Integer, nullable=False)  # 1-5
    review_text = db.Column(db.Text, nullable=True)
    verified = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default=ReviewStatus.ACTIVE)

    created_at = db.Column(db.DateTime, default=utcnow)

    user = db.relationship("User")

    @property
    def target_type(self):
        if self.product_id:
            return "PRODUCT"
        if self.service_id:
            return "SERVICE"
        return "SHOP"
