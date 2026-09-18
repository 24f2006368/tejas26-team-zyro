from datetime import datetime, timezone

from app.extensions import db

def utcnow():
    return datetime.now(timezone.utc)


class Service(db.Model):
    __tablename__ = "services"

    distance_km = None  # set dynamically by search_service; see Shop.distance_km

    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id"), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=True)
    price_type = db.Column(db.String(20), default="FIXED")  # FIXED / STARTING_FROM / ESTIMATE
    duration = db.Column(db.String(40), nullable=True)  # e.g. "30 min"

    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    reviews = db.relationship("Review", backref="service", lazy="dynamic")

    @property
    def rating_average(self):
        from app.constants import ReviewStatus
        ratings = [r.rating for r in self.reviews.filter_by(status=ReviewStatus.ACTIVE)]
        if not ratings:
            return None
        return round(sum(ratings) / len(ratings), 1)