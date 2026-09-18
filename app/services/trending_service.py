"""Trending vs. Popular scoring (doc #11/#49/#75). Kept as an isolated,
swappable module. MVP: Popular = total activity count; Trending = activity
in the last 48h relative to the previous 48h (rate of increase)."""
from datetime import datetime, timezone, timedelta

from sqlalchemy import func

from app.extensions import db
from app.models.notification import ActivityEvent
from app.models.shop import Shop


def log_event(shop_id, event_type, product_id=None):
    db.session.add(ActivityEvent(shop_id=shop_id, event_type=event_type, product_id=product_id))
    db.session.commit()


def popular_shops(limit=10):
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=30)
    rows = (
        db.session.query(ActivityEvent.shop_id, func.count(ActivityEvent.id).label("cnt"))
        .filter(ActivityEvent.created_at >= since)
        .group_by(ActivityEvent.shop_id)
        .order_by(func.count(ActivityEvent.id).desc())
        .limit(limit)
        .all()
    )
    shop_ids = [r.shop_id for r in rows]
    shops = {s.id: s for s in Shop.query.filter(Shop.id.in_(shop_ids)).all()} if shop_ids else {}
    return [shops[r.shop_id] for r in rows if r.shop_id in shops]


def trending_shops(limit=10):
    now = datetime.now(timezone.utc)
    recent_start = now - timedelta(hours=48)
    prior_start = now - timedelta(hours=96)

    recent = dict(
        db.session.query(ActivityEvent.shop_id, func.count(ActivityEvent.id))
        .filter(ActivityEvent.created_at >= recent_start)
        .group_by(ActivityEvent.shop_id).all()
    )
    prior = dict(
        db.session.query(ActivityEvent.shop_id, func.count(ActivityEvent.id))
        .filter(ActivityEvent.created_at >= prior_start, ActivityEvent.created_at < recent_start)
        .group_by(ActivityEvent.shop_id).all()
    )

    scored = []
    for shop_id, recent_count in recent.items():
        prior_count = prior.get(shop_id, 0)
        growth = recent_count - prior_count
        if recent_count >= 2:  # avoid noise from a single stray event
            scored.append((shop_id, growth, recent_count))

    scored.sort(key=lambda t: (t[1], t[2]), reverse=True)
    shop_ids = [s[0] for s in scored[:limit]]
    shops = {s.id: s for s in Shop.query.filter(Shop.id.in_(shop_ids)).all()} if shop_ids else {}
    return [shops[sid] for sid in shop_ids if sid in shops]
