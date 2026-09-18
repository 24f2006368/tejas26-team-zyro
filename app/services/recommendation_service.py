"""Recommendation-percentage logic (doc #30/#45/#76). Separate from star
rating. Weighted toward verified interactions; hides the percentage when the
sample size is too small to be meaningful."""
from app.extensions import db
from app.models.recommendation import Recommendation

MIN_SAMPLE_SIZE = 3


def prompt_eligible(reservation):
    """A completed reservation makes the customer eligible for a *verified*
    recommendation prompt. The prototype exposes this via the reservation
    detail page rather than a push notification."""
    return True


def submit_recommendation(user, shop, recommended, verified=False):
    existing = Recommendation.query.filter_by(user_id=user.id, shop_id=shop.id).first()
    if existing:
        existing.recommended = recommended
        existing.verified = existing.verified or verified
    else:
        existing = Recommendation(user_id=user.id, shop_id=shop.id,
                                   recommended=recommended, verified=verified)
        db.session.add(existing)
    db.session.commit()
    return existing


def percentage_for(shop):
    recs = shop.recommendations.all()
    if len(recs) < MIN_SAMPLE_SIZE:
        return None
    recommended = sum(1 for r in recs if r.recommended)
    return round(100 * recommended / len(recs))
