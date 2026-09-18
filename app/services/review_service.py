"""Review eligibility rules (improvement spec #5): a customer may only
review a shop/product after a genuine completed interaction — a FULFILLED
(collected) reservation. Pending/rejected/cancelled/expired reservations,
and simply viewing a page, never qualify. This is enforced here so the
backend — not just the frontend button — is the source of truth."""
from app.constants import ReservationStatus
from app.models.reservation import Reservation
from app.models.review import Review


def eligible_reservation(user_id, shop_id, product_id=None):
    """Returns the most recent qualifying reservation, or None."""
    if not shop_id:
        return None
    query = Reservation.query.filter_by(
        customer_id=user_id, shop_id=shop_id, status=ReservationStatus.FULFILLED,
    )
    if product_id:
        # A product-scoped review must trace back to a reservation of that
        # exact product (not merely any purchase at the shop).
        query = query.filter_by(product_id=product_id)
    return query.order_by(Reservation.completed_at.desc()).first()


def is_eligible(user_id, shop_id, product_id=None):
    return eligible_reservation(user_id, shop_id, product_id=product_id) is not None


def already_reviewed(user_id, shop_id, product_id=None):
    return Review.query.filter_by(
        user_id=user_id, shop_id=shop_id, product_id=product_id,
    ).first() is not None
