from datetime import datetime, timezone

from app.extensions import db
from app.constants import RegistrationMethod, VerificationStatus, ImageType, DocumentType


def utcnow():
    return datetime.now(timezone.utc)


class Shop(db.Model):
    __tablename__ = "shops"

    # Not a column — set dynamically by search_service for distance-ranked
    # results. Declared here so templates can read it unconditionally on
    # shops that were never distance-annotated (e.g. "Discover" listings).
    distance_km = None

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(150), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    subcategory_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)

    address = db.Column(db.String(255), nullable=True)
    locality = db.Column(db.String(120), nullable=True, index=True)
    city = db.Column(db.String(120), nullable=True, index=True)
    pincode = db.Column(db.String(10), nullable=True, index=True)
    latitude = db.Column(db.Float, nullable=False, index=True)
    longitude = db.Column(db.Float, nullable=False, index=True)

    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)

    opening_time = db.Column(db.String(10), nullable=True)   # "09:00"
    closing_time = db.Column(db.String(10), nullable=True)   # "21:00"
    working_days = db.Column(db.String(120), nullable=True)  # "Mon-Sat"

    registration_method = db.Column(db.String(10), default=RegistrationMethod.SELF)
    verification_status = db.Column(
        db.String(30), default=VerificationStatus.PENDING, index=True
    )
    verification_notes = db.Column(db.Text, nullable=True)
    verified_at = db.Column(db.DateTime, nullable=True)

    delivery_enabled = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    owner = db.relationship("User", back_populates="shops")
    category = db.relationship("Category", foreign_keys=[category_id])
    subcategory = db.relationship("Category", foreign_keys=[subcategory_id])

    offerings = db.relationship("BusinessOffering", backref="shop", lazy="dynamic",
                                 cascade="all, delete-orphan")
    products = db.relationship("Product", backref="shop", lazy="dynamic",
                                cascade="all, delete-orphan")
    services = db.relationship("Service", backref="shop", lazy="dynamic",
                                cascade="all, delete-orphan")
    documents = db.relationship("ShopDocument", backref="shop", lazy="dynamic",
                                 cascade="all, delete-orphan")
    images = db.relationship("ShopImage", backref="shop", lazy="dynamic",
                              cascade="all, delete-orphan")
    reviews = db.relationship("Review", backref="shop", lazy="dynamic",
                               cascade="all, delete-orphan")
    recommendations = db.relationship("Recommendation", backref="shop", lazy="dynamic",
                                       cascade="all, delete-orphan")

    @property
    def is_verified(self):
        return self.verification_status == VerificationStatus.APPROVED

    @property
    def rating_average(self):
        from app.models.review import Review
        from app.constants import ReviewStatus
        ratings = [r.rating for r in self.reviews.filter_by(status=ReviewStatus.ACTIVE)]
        if not ratings:
            return None
        return round(sum(ratings) / len(ratings), 1)

    @property
    def review_count(self):
        from app.constants import ReviewStatus
        return self.reviews.filter_by(status=ReviewStatus.ACTIVE).count()

    @property
    def recommendation_percentage(self):
        recs = self.recommendations.all()
        if len(recs) < 3:
            # Not enough verified sample size to show a confident number (doc #76).
            return None
        recommended = sum(1 for r in recs if r.recommended)
        return round(100 * recommended / len(recs))

    def front_image(self):
        img = self.images.filter_by(image_type=ImageType.FRONT).first()
        return img.image_path if img else None

    def __repr__(self):
        return f"<Shop {self.name}>"


class ShopDocument(db.Model):
    __tablename__ = "shop_documents"

    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id"), nullable=False)
    document_type = db.Column(db.String(30), default=DocumentType.OTHER)
    document_number = db.Column(db.String(80), nullable=True)
    document_file = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=utcnow)
    verified_at = db.Column(db.DateTime, nullable=True)


class ShopImage(db.Model):
    __tablename__ = "shop_images"

    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id"), nullable=False)
    image_type = db.Column(db.String(20), default=ImageType.OTHER)
    image_path = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)


class BusinessOffering(db.Model):
    """Lightweight 'what does this shop sell' entry — exists independently of
    a detailed, priced Product row (doc section 22: catalogue vs. detailed listing)."""
    __tablename__ = "business_offerings"

    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    type = db.Column(db.String(20), default="PRODUCT")  # PRODUCT / SERVICE
    category = db.Column(db.String(80), nullable=True)
    description = db.Column(db.String(255), nullable=True)