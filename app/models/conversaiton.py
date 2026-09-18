from datetime import datetime, timezone

from app.extensions import db

def utcnow():
    return datetime.now(timezone.utc)


class Conversation(db.Model):
    __tablename__ = "conversations"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True)

    created_at = db.Column(db.DateTime, default=utcnow)
    last_message_at = db.Column(db.DateTime, default=utcnow)

    customer = db.relationship("User")
    shop = db.relationship("Shop")
    product = db.relationship("Product")
    messages = db.relationship("Message", backref="conversation", lazy="dynamic",
                                order_by="Message.created_at",
                                cascade="all, delete-orphan")

    __table_args__ = (
        db.UniqueConstraint("customer_id", "shop_id", "product_id",
                             name="uq_conversation_customer_shop_product"),
    )
