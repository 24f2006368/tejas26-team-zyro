from app.extensions import db
from app.models.notification import Notification


def notify(user_id, ntype, title, message=None, link=None):
    n = Notification(user_id=user_id, type=ntype, title=title, message=message, link=link)
    db.session.add(n)
    db.session.commit()
    return n


def unread_count(user_id):
    return Notification.query.filter_by(user_id=user_id, is_read=False).count()


def mark_all_read(user_id):
    Notification.query.filter_by(user_id=user_id, is_read=False).update({"is_read": True})
    db.session.commit()
