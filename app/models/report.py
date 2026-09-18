from datetime import datetime, timezone

from app.extensions import db
from app.constants import ReportStatus

def utcnow():
    return datetime.now(timezone.utc)


class Report(db.Model):
    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    reported_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id"), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True)
    review_id = db.Column(db.Integer, db.ForeignKey("reviews.id"), nullable=True)
    report_type = db.Column(db.String(40), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default=ReportStatus.OPEN, index=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)

    reporter = db.relationship("User")
    shop = db.relationship("Shop")
    product = db.relationship("Product")
    review = db.relationship("Review")
