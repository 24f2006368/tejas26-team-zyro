from flask import Blueprint, render_template, request, redirect, url_for, jsonify, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.constants import Role, NotificationType
from app.models.shop import Shop
from app.models.product import Product
from app.models.conversation import Conversation
from app.models.message import Message
from app.services.notification_service import notify

chat_bp = Blueprint("chat", __name__, url_prefix="/chat")


def _authorize(conversation):
    """Chat security (doc #27/#81): a customer may only access conversations
    they are a participant in; a merchant only their own shop's conversations."""
    if current_user.is_admin:
        return
    if current_user.is_customer and conversation.customer_id == current_user.id:
        return
    if current_user.is_shopkeeper and conversation.shop.owner_id == current_user.id:
        return
    abort(403)


@chat_bp.route("/start", methods=["POST"])
@login_required
def start():
    if current_user.role not in (Role.CUSTOMER,):
        abort(403)
    shop = Shop.query.get_or_404(request.form.get("shop_id"))
    product_id = request.form.get("product_id") or None

    conversation = Conversation.query.filter_by(
        customer_id=current_user.id, shop_id=shop.id, product_id=product_id
    ).first()
    if not conversation:
        conversation = Conversation(customer_id=current_user.id, shop_id=shop.id, product_id=product_id)
        db.session.add(conversation)
        db.session.commit()

    return redirect(url_for("chat.view", conversation_id=conversation.id))


@chat_bp.route("/<int:conversation_id>")
@login_required
def view(conversation_id):
    conversation = Conversation.query.get_or_404(conversation_id)
    _authorize(conversation)

    other_is_customer = current_user.is_shopkeeper or current_user.is_admin
    unread = conversation.messages.filter(
        Message.sender_id != current_user.id, Message.is_read == False  # noqa: E712
    ).all()
    for m in unread:
        m.is_read = True
    if unread:
        db.session.commit()

    return render_template("chat/conversation.html", conversation=conversation)


@chat_bp.route("/<int:conversation_id>/send", methods=["POST"])
@login_required
def send(conversation_id):
    """AJAX/HTTP fallback for sending — the Socket.IO event does the same
    thing for the live, real-time path (see app/sockets/chat_events.py)."""
    conversation = Conversation.query.get_or_404(conversation_id)
    _authorize(conversation)

    text = request.form.get("message", "").strip()
    if not text:
        return jsonify({"error": "empty message"}), 400

    message = Message(conversation_id=conversation.id, sender_id=current_user.id, message=text)
    db.session.add(message)
    from datetime import datetime, timezone
    conversation.last_message_at = datetime.now(timezone.utc)
    db.session.commit()

    recipient_id = (conversation.shop.owner_id if current_user.id == conversation.customer_id
                     else conversation.customer_id)
    notify(recipient_id, NotificationType.NEW_CHAT, "New message", text[:80],
           link=url_for("chat.view", conversation_id=conversation.id))

    from app.extensions import socketio
    socketio.emit(
        "new_message",
        {
            "conversation_id": conversation.id,
            "sender_id": current_user.id,
            "sender_name": current_user.name,
            "message": text,
            "created_at": message.created_at.isoformat(),
        },
        room=f"conversation_{conversation.id}",
    )

    return jsonify({"ok": True})


@chat_bp.route("/<int:conversation_id>/quick-action", methods=["POST"])
@login_required
def quick_action(conversation_id):
    """Doc #22/#29 quick chat actions — reduces typing for both sides."""
    conversation = Conversation.query.get_or_404(conversation_id)
    _authorize(conversation)
    text = request.form.get("text", "").strip()
    if not text:
        return redirect(url_for("chat.view", conversation_id=conversation.id))

    message = Message(conversation_id=conversation.id, sender_id=current_user.id, message=text)
    db.session.add(message)
    from datetime import datetime, timezone
    conversation.last_message_at = datetime.now(timezone.utc)
    db.session.commit()

    from app.extensions import socketio
    socketio.emit(
        "new_message",
        {"conversation_id": conversation.id, "sender_id": current_user.id,
         "sender_name": current_user.name, "message": text,
         "created_at": message.created_at.isoformat()},
        room=f"conversation_{conversation.id}",
    )
    return redirect(url_for("chat.view", conversation_id=conversation.id))
