"""Seed realistic demo data for one local market (Sheikhpura Main Bazaar)
so the doc's demo scenarios (#89/#90) work out of the box:
  - "mechanic near me" -> multiple mechanics
  - "momos near me" -> street food stalls
  - "Samsung 25W charger" -> price comparison across shops
  - full chat -> reservation -> pickup/delivery loop
  - an admin verification queue with a pending business

Run with: python seed.py
"""
import os
import random
from datetime import datetime, timedelta, timezone

from app import create_app
from app.extensions import db
from app.constants import (
    Role, RegistrationMethod, VerificationStatus, AvailabilityStatus,
    ReservationStatus, CategoryType,
)
from app.models.user import User
from app.models.category import Category
from app.models.shop import Shop, BusinessOffering, ShopImage
from app.models.product import Product
from app.models.service import Service
from app.models.review import Review
from app.models.recommendation import Recommendation
from app.models.reservation import Reservation
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.notification import ActivityEvent

BASE_LAT, BASE_LON = 25.1417, 85.5350  # Sheikhpura, Bihar — one representative local market


def jitter(base, spread_km=1.2):
    delta = spread_km / 111.0
    return base + random.uniform(-delta, delta)


def get_or_create_category(name, ctype, parent=None):
    slug = name.lower().replace(" ", "-").replace("&", "and")
    cat = Category.query.filter_by(slug=slug).first()
    if not cat:
        cat = Category(name=name, slug=slug, type=ctype, parent_id=parent.id if parent else None)
        db.session.add(cat)
        db.session.flush()
    return cat


def make_user(name, email, phone, password, role, address=None):
    user = User.query.filter((User.email == email)).first()
    if user:
        return user
    user = User(name=name, email=email, phone=phone, role=role, address=address)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    return user


def make_shop(owner, name, category, description, locality, offerings,
              verification=VerificationStatus.APPROVED, delivery_enabled=False,
              opening="09:00", closing="21:00"):
    shop = Shop(
        owner_id=owner.id, name=name, description=description, category_id=category.id,
        address=f"{locality}, Sheikhpura Main Bazaar", locality=locality, city="Sheikhpura",
        pincode="811105", latitude=jitter(BASE_LAT), longitude=jitter(BASE_LON),
        phone=owner.phone, email=owner.email, opening_time=opening, closing_time=closing,
        working_days="Mon-Sat", registration_method=RegistrationMethod.SELF,
        verification_status=verification, delivery_enabled=delivery_enabled,
        verified_at=datetime.now(timezone.utc) if verification == VerificationStatus.APPROVED else None,
    )
    db.session.add(shop)
    db.session.flush()
    for o in offerings:
        db.session.add(BusinessOffering(shop_id=shop.id, name=o, type="PRODUCT"))
    return shop


def make_product(shop, name, brand, category, price, description, inventory_enabled=True,
                  discount_percent=None, sale_tag=None, minutes_ago=15):
    p = Product(
        shop_id=shop.id, name=name, brand=brand, category_id=category.id if category else None,
        description=description, price=price, inventory_enabled=inventory_enabled,
        availability_status=AvailabilityStatus.AVAILABLE if inventory_enabled else AvailabilityStatus.UNKNOWN,
        discount_percent=discount_percent, sale_tag=sale_tag,
        price_updated_at=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
    )
    db.session.add(p)
    db.session.flush()
    return p


def make_review(user, shop=None, product=None, rating=5, text="", verified=False, days_ago=1):
    r = Review(user_id=user.id, shop_id=shop.id if shop else None,
               product_id=product.id if product else None,
               rating=rating, review_text=text, verified=verified,
               created_at=datetime.now(timezone.utc) - timedelta(days=days_ago))
    db.session.add(r)


def seed():
    app = create_app()
    with app.app_context():
        if User.query.filter_by(email="admin@nearcart.local").first():
            print("Seed data already present. Skipping (delete nearcart.db to reseed).")
            return

        print("Seeding categories...")
        cat_electronics = get_or_create_category("Electronics", CategoryType.SHOP)
        cat_grocery = get_or_create_category("Grocery", CategoryType.SHOP)
        cat_clothing = get_or_create_category("Clothing", CategoryType.SHOP)
        cat_hardware = get_or_create_category("Hardware", CategoryType.SHOP)
        cat_stationery = get_or_create_category("Stationery", CategoryType.SHOP)
        cat_mechanic = get_or_create_category("Mechanic", CategoryType.SERVICE)
        cat_repair = get_or_create_category("Mobile Repair", CategoryType.SERVICE)
        cat_tailor = get_or_create_category("Tailor", CategoryType.SERVICE)
        cat_restaurant = get_or_create_category("Restaurants", CategoryType.FOOD)
        cat_street_food = get_or_create_category("Street Food", CategoryType.FOOD)
        cat_bakery = get_or_create_category("Bakeries", CategoryType.FOOD)
        cat_specialty = get_or_create_category("Local Specialties", CategoryType.SPECIALTY)
        cat_other = get_or_create_category("Other", CategoryType.OTHER)

        # A few subcategories so the registration flow's category -> subcategory
        # filtering has something real to demonstrate (doc section 39).
        get_or_create_category("Mobile Accessories", CategoryType.SHOP, parent=cat_electronics)
        get_or_create_category("Chargers", CategoryType.SHOP, parent=cat_electronics)
        get_or_create_category("Earphones", CategoryType.SHOP, parent=cat_electronics)
        get_or_create_category("Computer Accessories", CategoryType.SHOP, parent=cat_electronics)
        get_or_create_category("Auto Repair", CategoryType.SERVICE, parent=cat_mechanic)
        get_or_create_category("Two-Wheeler Service", CategoryType.SERVICE, parent=cat_mechanic)

        print("Seeding users...")
        admin = make_user("NearCart Admin", "admin@nearcart.local", "9000000000", "admin123", Role.ADMIN)
        priya = make_user("Priya Sharma", "priya@example.com", "9800000001", "password123", Role.CUSTOMER,
                           address="Station Road, Sheikhpura")
        amit = make_user("Amit Kumar", "amit@example.com", "9800000002", "password123", Role.CUSTOMER)
        rider = make_user("Ravi Rider", "ravi.rider@example.com", "9800000099", "password123", Role.DELIVERY_PARTNER)

        gupta_owner = make_user("Gupta Ji", "gupta.electronics@example.com", "9811100001", "password123", Role.SHOPKEEPER)
        mobile_point_owner = make_user("Sanjay Verma", "mobilepoint@example.com", "9811100002", "password123", Role.SHOPKEEPER)
        xyz_owner = make_user("Rakesh XYZ", "xyzelectronics@example.com", "9811100003", "password123", Role.SHOPKEEPER)
        raju_owner = make_user("Raju Yadav", "rajuauto@example.com", "9811100004", "password123", Role.SHOPKEEPER)
        aman_owner = make_user("Aman Singh", "amangarage@example.com", "9811100005", "password123", Role.SHOPKEEPER)
        kumar_owner = make_user("Kumar Ji", "kumarmotors@example.com", "9811100006", "password123", Role.SHOPKEEPER)
        sharma_momos_owner = make_user("Sharma Ji", "sharmamomos@example.com", "9811100007", "password123", Role.SHOPKEEPER)
        gupta_chaat_owner = make_user("Gupta Chaat Wale", "guptachaat@example.com", "9811100008", "password123", Role.SHOPKEEPER)
        mithai_owner = make_user("Bansal Mithai", "bansalmithai@example.com", "9811100009", "password123", Role.SHOPKEEPER)
        stationery_owner = make_user("Vikas Stationers", "vikasstationers@example.com", "9811100010", "password123", Role.SHOPKEEPER)
        tailor_owner = make_user("Master Tailor", "mastertailor@example.com", "9811100011", "password123", Role.SHOPKEEPER)
        newcomer_owner = make_user("New Shop Owner", "newtechpoint@example.com", "9811100012", "password123", Role.SHOPKEEPER)

        print("Seeding shops + catalogue...")

        gupta = make_shop(gupta_owner, "Gupta Electronics", cat_electronics,
                           "Electronics & mobile accessories — chargers, cables, earphones, power banks.",
                           "Main Bazaar Road", ["Chargers", "USB Cables", "Earphones", "Power Banks", "Batteries"],
                           delivery_enabled=True)
        mobile_point = make_shop(mobile_point_owner, "Mobile Point", cat_electronics,
                                  "Mobile accessories at the best local prices.",
                                  "Station Road", ["Chargers", "Screen Protectors", "Cases", "Cables"])
        xyz = make_shop(xyz_owner, "XYZ Electronics", cat_electronics,
                         "Trusted electronics store, slightly higher-end selection.",
                         "College Road", ["Chargers", "Laptops", "Accessories"])
        newtech = make_shop(newcomer_owner, "New Tech Point", cat_electronics,
                             "Newly opened gadget store.", "Bus Stand Road",
                             ["Chargers", "Bluetooth Speakers"], verification=VerificationStatus.PENDING)

        make_product(gupta, "Samsung 25W Fast Charger", "Samsung", cat_electronics, 499,
                     "25W fast charging, USB-C, original Samsung adapter.", minutes_ago=18)
        make_product(gupta, "Type-C Cable 1m", "Samsung", cat_electronics, 249, "Durable braided Type-C cable.")
        make_product(gupta, "Wired Earphones", "boAt", cat_electronics, 349, "In-ear wired earphones with mic.")
        make_product(mobile_point, "Samsung 25W Fast Charger", "Samsung", cat_electronics, 475,
                     "25W fast charger, USB-C.", minutes_ago=40)
        make_product(mobile_point, "Screen Protector", "Generic", cat_electronics, 99, "Tempered glass screen guard.")
        make_product(xyz, "Samsung 25W Fast Charger", "Samsung", cat_electronics, 520,
                     "Samsung original fast charger with warranty.", minutes_ago=5)
        make_product(newtech, "Samsung 25W Fast Charger", "Samsung", cat_electronics, 459,
                     "New store — introductory pricing.", discount_percent=10, sale_tag="Opening Offer")

        raju = make_shop(raju_owner, "Raju Auto Works", cat_mechanic,
                          "Bike repair, puncture and oil change specialists.", "Bypass Road",
                          ["Bike Servicing", "Puncture Repair", "Oil Change"])
        aman = make_shop(aman_owner, "Aman Garage", cat_mechanic,
                          "General bike and scooter repair.", "Old Bus Stand",
                          ["Bike Servicing", "Brake Repair"])
        kumar = make_shop(kumar_owner, "Kumar Motors", cat_mechanic,
                           "Multi-brand two-wheeler service center.", "GT Road",
                           ["Bike Servicing", "Puncture Repair", "Battery Replacement"])
        for shop, services in [
            (raju, [("Bike Servicing", 250, "FIXED", "45 min"), ("Puncture Repair", 60, "FIXED", "15 min"),
                    ("Oil Change", 150, "STARTING_FROM", "20 min")]),
            (aman, [("Bike Servicing", 220, "FIXED", "40 min"), ("Brake Repair", 180, "ESTIMATE", "30 min")]),
            (kumar, [("Bike Servicing", 280, "FIXED", "50 min"), ("Puncture Repair", 50, "FIXED", "15 min"),
                     ("Battery Replacement", 900, "STARTING_FROM", "20 min")]),
        ]:
            for name, price, ptype, duration in services:
                db.session.add(Service(shop_id=shop.id, name=name, price=price, price_type=ptype, duration=duration))

        sharma_momos = make_shop(sharma_momos_owner, "Sharma Momos", cat_street_food,
                                  "Famous fried and steamed momos stall.", "Main Chowk",
                                  ["Steamed Momos", "Fried Momos", "Chutney"], opening="12:00", closing="21:00")
        gupta_chaat = make_shop(gupta_chaat_owner, "Gupta Chaat", cat_street_food,
                                 "Local favourite for chaat and golgappe.", "Main Chowk",
                                 ["Golgappe", "Aloo Tikki", "Bhel Puri"], opening="14:00", closing="22:00")
        bansal_mithai = make_shop(mithai_owner, "Bansal Traditional Mithai", cat_specialty,
                                   "Local specialty sweet shop, famous for decades.", "Main Bazaar Road",
                                   ["Laddoo", "Barfi", "Rasgulla"])

        make_product(sharma_momos, "Steamed Momos (Veg)", None, cat_street_food, 60, "6 pieces, served with chutney.")
        make_product(sharma_momos, "Fried Momos (Chicken)", None, cat_street_food, 120, "6 pieces, crispy fried.")
        make_product(gupta_chaat, "Golgappe (Plate)", None, cat_street_food, 40, "6 pieces spicy pani puri.")
        make_product(bansal_mithai, "Besan Laddoo (500g)", None, cat_specialty, 220, "Traditional besan laddoo.")

        vikas = make_shop(stationery_owner, "Vikas Stationers", cat_stationery,
                           "Notebooks, pens, art supplies and Arduino components.", "College Road",
                           ["Notebooks", "Pens", "Art Supplies", "Arduino Components"])
        make_product(vikas, "Arduino Uno R3 (Compatible)", "Generic", cat_stationery, 399, "Arduino Uno compatible board.")
        make_product(vikas, "A4 Notebook (Set of 5)", "Classmate", cat_stationery, 199, "Ruled A4 notebooks.")

        master_tailor = make_shop(tailor_owner, "Master Tailor", cat_tailor,
                                   "Custom stitching and alterations.", "Station Road", ["Stitching", "Alterations"])
        db.session.add(Service(shop_id=master_tailor.id, name="Shirt Stitching", price=350, price_type="FIXED", duration="3 days"))
        db.session.add(Service(shop_id=master_tailor.id, name="Alteration", price=100, price_type="STARTING_FROM", duration="1 day"))

        db.session.flush()

        print("Seeding reviews & recommendations...")
        make_review(priya, shop=gupta, rating=5, text="Genuine products, quick service.", verified=True, days_ago=2)
        make_review(amit, shop=gupta, rating=4, text="Good prices, slightly crowded in evenings.", days_ago=5)
        make_review(priya, shop=raju, rating=5, text="Fixed my puncture in 10 minutes!", verified=True, days_ago=1)
        make_review(amit, shop=sharma_momos, rating=5, text="Best momos in the bazaar.", verified=True, days_ago=3)
        make_review(priya, shop=sharma_momos, rating=4, text="Tasty but a bit spicy for me.", days_ago=6)

        for user in [priya, amit]:
            db.session.add(Recommendation(user_id=user.id, shop_id=gupta.id, recommended=True, verified=True))
            db.session.add(Recommendation(user_id=user.id, shop_id=raju.id, recommended=True, verified=True))
            db.session.add(Recommendation(user_id=user.id, shop_id=sharma_momos.id, recommended=True, verified=True))
        db.session.add(Recommendation(user_id=priya.id, shop_id=xyz.id, recommended=True, verified=False))
        db.session.add(Recommendation(user_id=amit.id, shop_id=xyz.id, recommended=False, verified=False))

        print("Seeding a sample chat + reservation...")
        gupta_charger = Product.query.filter_by(shop_id=gupta.id, name="Samsung 25W Fast Charger").first()
        conversation = Conversation(customer_id=priya.id, shop_id=gupta.id, product_id=gupta_charger.id)
        db.session.add(conversation)
        db.session.flush()
        db.session.add_all([
            Message(conversation_id=conversation.id, sender_id=priya.id, message="Samsung 25W charger available hai?", is_read=True),
            Message(conversation_id=conversation.id, sender_id=gupta_owner.id, message="Haan, available hai.", is_read=True),
            Message(conversation_id=conversation.id, sender_id=priya.id, message="Reserve kar dijiye.", is_read=False),
        ])

        reservation = Reservation(customer_id=priya.id, shop_id=gupta.id, product_id=gupta_charger.id,
                                   quantity=1, status=ReservationStatus.PENDING,
                                   expires_at=datetime.now(timezone.utc) + timedelta(hours=24))
        db.session.add(reservation)

        print("Seeding activity signals (for trending)...")
        now = datetime.now(timezone.utc)
        for shop, count, recent_boost in [(sharma_momos, 8, 12), (gupta, 6, 2), (raju, 4, 1), (newtech, 2, 6)]:
            for i in range(count):
                db.session.add(ActivityEvent(shop_id=shop.id, event_type="VIEW",
                                              created_at=now - timedelta(hours=90 - i)))
            for i in range(recent_boost):
                db.session.add(ActivityEvent(shop_id=shop.id, event_type="VIEW",
                                              created_at=now - timedelta(hours=i * 2)))

        db.session.commit()
        print("Done. Seeded Sheikhpura Main Bazaar demo data.")
        print("Admin: admin@nearcart.local / admin123")
        print("Customer: priya@example.com / password123")
        print("Shopkeeper: gupta.electronics@example.com / password123")
        print("Delivery partner: ravi.rider@example.com / password123")
        print(f"New Tech Point ({newtech.id}) is left PENDING verification for the admin demo scenario.")


if __name__ == "__main__":
    seed()
