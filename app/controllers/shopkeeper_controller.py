from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_user, current_user, login_required

from app.extensions import db
from app.constants import (
    Role, RegistrationMethod, VerificationStatus, ImageType, DocumentType,
    ReservationStatus, ProductStatus, AvailabilityStatus,
)
from app.models.user import User
from app.models.shop import Shop, ShopImage, ShopDocument, BusinessOffering
from app.models.category import Category
from app.models.product import Product
from app.models.service import Service
from app.models.reservation import Reservation
from app.models.conversation import Conversation
from app.models.review import Review
from app.services import file_service, reservation_service, delivery_service, ai_service
from app.controllers.helpers import role_required

shopkeeper_bp = Blueprint("shopkeeper", __name__, url_prefix="/shopkeeper")


def _current_shop():
    shop = Shop.query.filter_by(owner_id=current_user.id).first()
    if not shop:
        abort(404)
    return shop


# ---------------------------------------------------------------- REGISTRATION

@shopkeeper_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        flash("Log out of your current account before registering a business.", "error")
        return redirect(url_for("main.home"))

    from app.constants import CategoryType

    all_shop_categories = Category.query.filter(Category.type.in_(CategoryType.REGISTRABLE)).all()
    other_category = Category.query.filter_by(type=CategoryType.OTHER, parent_id=None).first()

    if request.method == "POST":
        f = request.form
        errors = []

        owner_name = f.get("owner_name", "").strip()
        owner_email = f.get("owner_email", "").strip() or None
        owner_phone = f.get("owner_phone", "").strip() or None
        password = f.get("password", "")
        confirm_password = f.get("confirm_password", "")

        shop_name = f.get("shop_name", "").strip()
        category_id_raw = f.get("category_id", "").strip()
        subcategory_id_raw = f.get("subcategory_id", "").strip()
        custom_category_name = f.get("custom_category_name", "").strip()
        custom_subcategory_name = f.get("custom_subcategory_name", "").strip()
        description = f.get("description", "").strip()
        address = f.get("address", "").strip()
        locality = f.get("locality", "").strip()
        city = f.get("city", "").strip()
        pincode = f.get("pincode", "").strip()
        opening_time = f.get("opening_time", "").strip()
        closing_time = f.get("closing_time", "").strip()
        working_days = f.get("working_days", "").strip()
        latitude = f.get("latitude")
        longitude = f.get("longitude")
        registration_method = f.get("registration_method", RegistrationMethod.SELF)
        offerings_raw = f.get("offerings", "")

        # ---- Step 1: Owner ----
        if not owner_name:
            errors.append("Owner name is required.")
        if not owner_email and not owner_phone:
            errors.append("Provide an owner email or phone number.")

        # ---- Step 2: Shop ----
        if not shop_name:
            errors.append("Shop name is required.")

        # ---- Step 3: Category (never trust the frontend dropdown) ----
        category = None
        subcategory = None
        if not category_id_raw:
            errors.append("Choose a category.")
        else:
            category = Category.query.filter(
                Category.id == _safe_int(category_id_raw),
                Category.parent_id.is_(None),
            ).first()
            if not category:
                errors.append("Selected category is not valid.")

        is_other_category = bool(category and category.type == CategoryType.OTHER)
        if is_other_category and not custom_category_name:
            errors.append("Enter your business category.")

        if subcategory_id_raw == "other":
            if not custom_subcategory_name:
                errors.append("Enter your business subcategory.")
        elif subcategory_id_raw:
            subcategory = Category.query.filter_by(id=_safe_int(subcategory_id_raw)).first()
            if not subcategory or not category or subcategory.parent_id != category.id:
                errors.append("Selected subcategory does not belong to the selected category.")
                subcategory = None

        # ---- Step 7: Location ----
        if not latitude or not longitude:
            errors.append("Please set your business location on the map.")

        # ---- Step 8: Password ----
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if password != confirm_password:
            errors.append("Passwords do not match.")

        if owner_email and User.query.filter_by(email=owner_email).first():
            errors.append("An account with this email already exists.")
        if owner_phone and User.query.filter_by(phone=owner_phone).first():
            errors.append("An account with this phone number already exists.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template(
                "shopkeeper/register.html", form=f,
                categories=all_shop_categories, other_category=other_category,
            )

        owner = User(name=owner_name, email=owner_email, phone=owner_phone,
                      address=f.get("owner_address", "").strip() or None, role=Role.SHOPKEEPER)
        owner.set_password(password)
        db.session.add(owner)
        db.session.flush()

        shop = Shop(
            owner_id=owner.id,
            name=shop_name,
            description=description,
            category_id=category.id,
            subcategory_id=subcategory.id if subcategory else None,
            custom_category_name=custom_category_name if is_other_category else None,
            custom_subcategory_name=custom_subcategory_name if subcategory_id_raw == "other" else None,
            address=address, locality=locality, city=city, pincode=pincode,
            latitude=float(latitude), longitude=float(longitude),
            phone=owner_phone, email=owner_email,
            opening_time=opening_time, closing_time=closing_time, working_days=working_days,
            registration_method=registration_method,
            verification_status=VerificationStatus.PENDING,
        )
        db.session.add(shop)
        db.session.flush()

        for line in offerings_raw.splitlines():
            line = line.strip()
            if line:
                db.session.add(BusinessOffering(shop_id=shop.id, name=line, type="PRODUCT"))

        # Verification documents
        doc_type = f.get("document_type")
        doc_file = request.files.get("document_file")
        if doc_type and doc_file and doc_file.filename:
            try:
                path = file_service.save_document(doc_file)
                db.session.add(ShopDocument(shop_id=shop.id, document_type=doc_type,
                                             document_number=f.get("document_number", ""),
                                             document_file=path))
            except file_service.InvalidFile as e:
                flash(str(e), "error")

        # Images
        image_map = {
            ImageType.FRONT: "image_front",
            ImageType.INTERIOR: "image_interior",
            ImageType.OWNER: "image_owner",
            ImageType.SIGNBOARD: "image_signboard",
        }
        for image_type, field in image_map.items():
            file = request.files.get(field)
            if file and file.filename:
                try:
                    path = file_service.save_image(file, file_service.SHOP_SUBDIR)
                    db.session.add(ShopImage(shop_id=shop.id, image_type=image_type, image_path=path))
                except file_service.InvalidFile as e:
                    flash(str(e), "error")

        db.session.commit()
        login_user(owner)
        flash("Your business has been submitted for verification. You can add products while you wait.", "success")
        return redirect(url_for("shopkeeper.home"))

    return render_template(
        "shopkeeper/register.html", form={},
        categories=all_shop_categories, other_category=other_category,
    )


def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- DASHBOARD

@shopkeeper_bp.route("/")
@login_required
@role_required(Role.SHOPKEEPER)
def home():
    shop = _current_shop()
    product_count = shop.products.count()
    new_reservations = Reservation.query.filter_by(
        shop_id=shop.id, status=ReservationStatus.PENDING
    ).count()
    unread_messages = 0
    for c in Conversation.query.filter_by(shop_id=shop.id).all():
        unread_messages += c.messages.filter_by(is_read=False).filter(
            Message_sender_is_customer(c)
        ).count()
    recent_reviews = shop.reviews.order_by(Review.created_at.desc()).limit(5).all()

    return render_template(
        "shopkeeper/home.html", shop=shop, product_count=product_count,
        new_reservations=new_reservations, unread_messages=unread_messages,
        recent_reviews=recent_reviews,
    )


def Message_sender_is_customer(conversation):
    from app.models.message import Message
    return Message.sender_id == conversation.customer_id


# ---------------------------------------------------------------- SHOP PROFILE

@shopkeeper_bp.route("/profile", methods=["GET", "POST"])
@login_required
@role_required(Role.SHOPKEEPER)
def profile():
    shop = _current_shop()
    if request.method == "POST":
        f = request.form
        shop.name = f.get("shop_name", shop.name).strip()
        shop.description = f.get("description", shop.description)
        shop.address = f.get("address", shop.address)
        shop.locality = f.get("locality", shop.locality)
        shop.city = f.get("city", shop.city)
        shop.pincode = f.get("pincode", shop.pincode)
        shop.opening_time = f.get("opening_time", shop.opening_time)
        shop.closing_time = f.get("closing_time", shop.closing_time)
        shop.working_days = f.get("working_days", shop.working_days)
        shop.delivery_enabled = f.get("delivery_enabled") == "on"
        if f.get("latitude") and f.get("longitude"):
            shop.latitude = float(f["latitude"])
            shop.longitude = float(f["longitude"])
        db.session.commit()
        flash("Shop profile updated.", "success")
        return redirect(url_for("shopkeeper.profile"))

    categories = Category.query.filter(Category.type.in_(["SHOP", "SERVICE", "FOOD"])).all()
    return render_template("shopkeeper/profile.html", shop=shop, categories=categories)


# ---------------------------------------------------------------- PRODUCTS

@shopkeeper_bp.route("/products")
@login_required
@role_required(Role.SHOPKEEPER)
def products():
    shop = _current_shop()
    items = shop.products.order_by(Product.updated_at.desc()).all()
    categories = Category.query.filter_by(type="SHOP").all()
    return render_template("shopkeeper/products.html", shop=shop, products=items, categories=categories)


@shopkeeper_bp.route("/products/add", methods=["POST"])
@login_required
@role_required(Role.SHOPKEEPER)
def add_product():
    shop = _current_shop()
    f = request.form
    name = f.get("name", "").strip()
    if not name:
        flash("Product name is required.", "error")
        return redirect(url_for("shopkeeper.products"))

    image_path = None
    file = request.files.get("image")
    if file and file.filename:
        try:
            image_path = file_service.save_image(file, file_service.PRODUCT_SUBDIR)
        except file_service.InvalidFile as e:
            flash(str(e), "error")

    product = Product(
        shop_id=shop.id, name=name, brand=f.get("brand", "").strip() or None,
        category_id=int(f["category_id"]) if f.get("category_id") else None,
        description=f.get("description", "").strip() or None,
        image=image_path,
        price=float(f["price"]) if f.get("price") else None,
        barcode=f.get("barcode", "").strip() or None,
        sku=f.get("sku", "").strip() or None,
        inventory_enabled=f.get("inventory_enabled") == "on",
        availability_status=(AvailabilityStatus.AVAILABLE if f.get("inventory_enabled") == "on"
                              else AvailabilityStatus.UNKNOWN),
    )
    db.session.add(product)
    db.session.commit()
    flash(f'"{product.name}" was added to your catalogue.', "success")
    return redirect(url_for("shopkeeper.products"))


@shopkeeper_bp.route("/products/<int:product_id>/edit", methods=["POST"])
@login_required
@role_required(Role.SHOPKEEPER)
def edit_product(product_id):
    shop = _current_shop()
    product = Product.query.filter_by(id=product_id, shop_id=shop.id).first_or_404()
    f = request.form

    old_price = product.price
    product.name = f.get("name", product.name).strip()
    product.brand = f.get("brand", product.brand)
    product.description = f.get("description", product.description)
    if f.get("price"):
        new_price = float(f["price"])
        if new_price != old_price:
            from datetime import datetime, timezone
            product.price_updated_at = datetime.now(timezone.utc)
        product.price = new_price
    product.discount_percent = float(f["discount_percent"]) if f.get("discount_percent") else None
    product.sale_tag = f.get("sale_tag", "").strip() or None
    product.barcode = f.get("barcode", product.barcode)

    file = request.files.get("image")
    if file and file.filename:
        try:
            product.image = file_service.save_image(file, file_service.PRODUCT_SUBDIR)
        except file_service.InvalidFile as e:
            flash(str(e), "error")

    db.session.commit()
    flash("Product updated.", "success")
    return redirect(url_for("shopkeeper.products"))


@shopkeeper_bp.route("/products/<int:product_id>/availability", methods=["POST"])
@login_required
@role_required(Role.SHOPKEEPER)
def set_availability(product_id):
    shop = _current_shop()
    product = Product.query.filter_by(id=product_id, shop_id=shop.id).first_or_404()
    status = request.form.get("status")
    if status in AvailabilityStatus.ALL:
        product.availability_status = status
        db.session.commit()
        flash("Availability updated.", "success")
    return redirect(url_for("shopkeeper.products"))


@shopkeeper_bp.route("/products/<int:product_id>/disable", methods=["POST"])
@login_required
@role_required(Role.SHOPKEEPER)
def disable_product(product_id):
    shop = _current_shop()
    product = Product.query.filter_by(id=product_id, shop_id=shop.id).first_or_404()
    product.status = (ProductStatus.INACTIVE if product.status == ProductStatus.ACTIVE
                       else ProductStatus.ACTIVE)
    db.session.commit()
    return redirect(url_for("shopkeeper.products"))


@shopkeeper_bp.route("/products/barcode-lookup")
@login_required
@role_required(Role.SHOPKEEPER)
def barcode_lookup():
    """Barcode workflow (doc #37/#79): look up an existing product by barcode
    within THIS shop's own catalogue (a real deployment would also query a
    public barcode database). Always falls back to manual entry."""
    shop = _current_shop()
    code = request.args.get("code", "").strip()
    product = Product.query.filter_by(shop_id=shop.id, barcode=code).first() if code else None
    from flask import jsonify
    if product:
        return jsonify({"found": True, "name": product.name, "brand": product.brand,
                         "price": product.price})
    return jsonify({"found": False})


# ---------------------------------------------------------------- SERVICES

@shopkeeper_bp.route("/services")
@login_required
@role_required(Role.SHOPKEEPER)
def services():
    shop = _current_shop()
    items = shop.services.order_by(Service.updated_at.desc()).all()
    return render_template("shopkeeper/services.html", shop=shop, services=items)


@shopkeeper_bp.route("/services/add", methods=["POST"])
@login_required
@role_required(Role.SHOPKEEPER)
def add_service():
    shop = _current_shop()
    f = request.form
    name = f.get("name", "").strip()
    if not name:
        flash("Service name is required.", "error")
        return redirect(url_for("shopkeeper.services"))
    service = Service(
        shop_id=shop.id, name=name, description=f.get("description", "").strip() or None,
        price=float(f["price"]) if f.get("price") else None,
        price_type=f.get("price_type", "FIXED"),
        duration=f.get("duration", "").strip() or None,
    )
    db.session.add(service)
    db.session.commit()
    flash(f'"{service.name}" was added.', "success")
    return redirect(url_for("shopkeeper.services"))


@shopkeeper_bp.route("/services/<int:service_id>/edit", methods=["POST"])
@login_required
@role_required(Role.SHOPKEEPER)
def edit_service(service_id):
    shop = _current_shop()
    service = Service.query.filter_by(id=service_id, shop_id=shop.id).first_or_404()
    f = request.form
    service.name = f.get("name", service.name).strip()
    service.description = f.get("description", service.description)
    service.price = float(f["price"]) if f.get("price") else service.price
    service.price_type = f.get("price_type", service.price_type)
    service.duration = f.get("duration", service.duration)
    db.session.commit()
    flash("Service updated.", "success")
    return redirect(url_for("shopkeeper.services"))


# ---------------------------------------------------------------- RESERVATIONS

@shopkeeper_bp.route("/reservations")
@login_required
@role_required(Role.SHOPKEEPER)
def reservations():
    shop = _current_shop()
    tab = request.args.get("tab", "pending").upper()
    status_map = {
        "PENDING": [ReservationStatus.PENDING],
        "CONFIRMED": [ReservationStatus.CONFIRMED],
        "READY": [ReservationStatus.READY],
        "COMPLETED": [ReservationStatus.FULFILLED, ReservationStatus.CANCELLED, ReservationStatus.REJECTED, ReservationStatus.EXPIRED],
    }
    statuses = status_map.get(tab, status_map["PENDING"])
    items = (Reservation.query.filter_by(shop_id=shop.id)
             .filter(Reservation.status.in_(statuses))
             .order_by(Reservation.requested_at.desc()).all())
    for item in items:
        reservation_service.sync_expiry(item)
    return render_template("shopkeeper/reservations.html", shop=shop, reservations=items, tab=tab.lower())


@shopkeeper_bp.route("/reservations/<int:reservation_id>/<action>", methods=["POST"])
@login_required
@role_required(Role.SHOPKEEPER)
def reservation_action(reservation_id, action):
    shop = _current_shop()
    reservation = Reservation.query.filter_by(id=reservation_id, shop_id=shop.id).first_or_404()
    try:
        if action == "confirm":
            reservation_service.confirm(reservation)
            flash("Reservation confirmed.", "success")
        elif action == "reject":
            reservation_service.reject(reservation, reason=request.form.get("reason"))
            flash("Reservation rejected.", "success")
        elif action == "ready":
            reservation_service.mark_ready(reservation)
            flash("Marked ready for pickup/delivery.", "success")
        elif action == "complete":
            reservation_service.complete(reservation)
            flash("Reservation marked complete.", "success")
        else:
            abort(404)
    except reservation_service.InvalidTransition as e:
        flash(str(e), "error")
    return redirect(url_for("shopkeeper.reservations", tab=request.form.get("tab", "pending")))


# ---------------------------------------------------------------- MESSAGES

@shopkeeper_bp.route("/messages")
@login_required
@role_required(Role.SHOPKEEPER)
def messages():
    shop = _current_shop()
    conversations = (Conversation.query.filter_by(shop_id=shop.id)
                      .order_by(Conversation.last_message_at.desc()).all())
    return render_template("shopkeeper/messages.html", shop=shop, conversations=conversations)


# ---------------------------------------------------------------- REVIEWS

@shopkeeper_bp.route("/reviews")
@login_required
@role_required(Role.SHOPKEEPER)
def reviews():
    shop = _current_shop()
    shop_reviews = shop.reviews.filter_by(product_id=None, service_id=None).order_by(Review.created_at.desc()).all()
    product_reviews = (Review.query.join(Product, Review.product_id == Product.id)
                        .filter(Product.shop_id == shop.id).order_by(Review.created_at.desc()).all())
    return render_template("shopkeeper/reviews.html", shop=shop, shop_reviews=shop_reviews,
                            product_reviews=product_reviews)

