from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db
from app.constants import Role


def utcnow():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, index=True, nullable=True)
    phone = db.Column(db.String(20), unique=True, index=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=Role.CUSTOMER)
    address = db.Column(db.String(255), nullable=True)
    profile_image = db.Column(db.String(255), nullable=True)
    is_active_account = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    shops = db.relationship("Shop", back_populates="owner", lazy="dynamic")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_customer(self):
        return self.role == Role.CUSTOMER

    @property
    def is_shopkeeper(self):
        return self.role == Role.SHOPKEEPER

    @property
    def is_admin(self):
        return self.role == Role.ADMIN

    @property
    def is_delivery_partner(self):
        return self.role == Role.DELIVERY_PARTNER

    def __repr__(self):
        return f"<User {self.id} {self.name} ({self.role})>"
