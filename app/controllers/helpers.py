from functools import wraps

from flask import abort
from flask_login import current_user


def role_required(*roles):
    """Backend-enforced role check (doc #69/#79: never trust the browser)."""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def owns_shop_or_403(shop):
    from flask_login import current_user
    if not current_user.is_authenticated:
        abort(403)
    if current_user.is_admin:
        return
    if not current_user.is_shopkeeper or shop.owner_id != current_user.id:
        abort(403)
