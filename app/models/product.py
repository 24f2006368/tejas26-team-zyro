from datetime import datetime, timezone

from app.extensions import db
from app.constants import ProductStatus, AvailabilityStatus


def utcnow():
    return datetime.now(timezone.utc)


class Product(db.Model):
    __tablename__ = "products"

    distance_km = None  # set dynamically by search_service; see Shop.distance_km

    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id"), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    brand = db.Column(db.String(80), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True, index=True)
    description = db.Column(db.Text, nullable=True)
    image = db.Column(db.String(255), nullable=True)

    price = db.Column(db.Float, nullable=True)
    discount_percent = db.Column(db.Float, nullable=True)
    sale_tag = db.Column(db.String(40), nullable=True)

    barcode = db.Column(db.String(64), nullable=True, index=True)
    sku = db.Column(db.String(64), nullable=True)

    inventory_enabled = db.Column(db.Boolean, default=False)
    availability_status = db.Column(db.String(20), default=AvailabilityStatus.UNKNOWN)
    status = db.Column(db.String(20), default=ProductStatus.ACTIVE)

    price_updated_at = db.Column(db.DateTime, default=utcnow)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    category = db.relationship("Category")
    reviews = db.relationship("Review", backref="product", lazy="dynamic")

    @property
    def discounted_price(self):
        if self.price is None:
            return None
        if self.discount_percent:
            return round(self.price * (1 - self.discount_percent / 100), 2)
        return self.price

    @property
    def rating_average(self):
        from app.constants import ReviewStatus
        ratings = [r.rating for r in self.reviews.filter_by(status=ReviewStatus.ACTIVE)]
        if not ratings:
            return None
        return round(sum(ratings) / len(ratings), 1)

    @property
    def review_count(self):
        from app.constants import ReviewStatus
        return self.reviews.filter_by(status=ReviewStatus.ACTIVE).count()

    def __repr__(self):
        return f"<Product {self.name} @ shop {self.shop_id}>"