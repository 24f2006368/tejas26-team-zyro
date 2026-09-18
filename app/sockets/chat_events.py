"""Flask-SocketIO event handlers (doc #21/#63). Messages are always
persisted through the same authorization check as the HTTP fallback route —
Socket.IO is a transport, not a bypass for access control."""
from flask_login import current_user
from flask_socketio import join_room, emit

from app.extensions import socketio, db
from app.models.conversation import Conversation
from app.models.message import Message


def _authorized(conversation):
    if not current_user.is_authenticated:
        return False
    if current_user.is_admin:
        return True
    if current_user.is_customer and conversation.customer_id == current_user.id:
        return True
    if current_user.is_shopkeeper and conversation.shop.owner_id == current_user.id:
        return True
    return False


@socketio.on("join_conversation")
def handle_join(data):
    conversation = Conversation.query.get(data.get("conversation_id"))
    if not conversation or not _authorized(conversation):
        return
    join_room(f"conversation_{conversation.id}")


@socketio.on("send_message")
def handle_send(data):
    conversation = Conversation.query.get(data.get("conversation_id"))
    if not conversation or not _authorized(conversation):
        return
    text = (data.get("message") or "").strip()
    if not text:
        return

    message = Message(conversation_id=conversation.id, sender_id=current_user.id, message=text)
    db.session.add(message)
    from datetime import datetime, timezone
    conversation.last_message_at = datetime.now(timezone.utc)
    db.session.commit()

    emit(
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
