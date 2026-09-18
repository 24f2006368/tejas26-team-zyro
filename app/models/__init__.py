"""Import every model so db.create_all() / Alembic can discover them."""
from app.models.user import User
from app.models.category import Category
from app.models.shop import Shop, ShopDocument, ShopImage, BusinessOffering
from app.models.product import Product
from app.models.service import Service
from app.models.review import Review
from app.models.recommendation import Recommendation
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.reservation import Reservation
from app.models.delivery import Delivery
from app.models.report import Report
from app.models.notification import Notification, SavedItem, ActivityEvent

__all__ = [
    "User", "Category", "Shop", "ShopDocument", "ShopImage", "BusinessOffering",
    "Product", "Service", "Review", "Recommendation", "Conversation", "Message",
    "Reservation", "Delivery", "Report", "Notification", "SavedItem", "ActivityEvent",
]
