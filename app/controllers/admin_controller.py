# first
import os

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, send_from_directory, send_file, current_app
from flask_login import login_required, current_user

from app.extensions import db
from app.constants import Role, VerificationStatus, ReportStatus, ReviewStatus, NotificationType
from app.models.user import User
from app.models.shop import Shop, ShopDocument, ShopImage
from app.models.product import Product
from app.models.review import Review
from app.models.report import Report
from app.models.reservation import Reservation
from app.models.conversation import Conversation
from app.services.notification_service import notify
from app.services import analytics_report_service, report_export_service
from app.controllers.helpers import role_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@login_required
@role_required(Role.ADMIN)
def overview():
    stats = {
        "total_customers": User.query.filter_by(role=Role.CUSTOMER).count(),
        "total_businesses": Shop.query.count(),
        "pending_businesses": Shop.query.filter_by(verification_status=VerificationStatus.PENDING).count(),
        "verified_businesses": Shop.query.filter_by(verification_status=VerificationStatus.APPROVED).count(),
        "total_products": Product.query.count(),
        "total_reservations": Reservation.query.count(),
        "active_conversations": Conversation.query.count(),
        "open_reports": Report.query.filter_by(status=ReportStatus.OPEN).count(),
    }
    recent_shops = Shop.query.order_by(Shop.created_at.desc()).limit(6).all()
    return render_template("admin/overview.html", stats=stats, recent_shops=recent_shops)


# ---------------------------------------------------------------- VERIFICATION

@admin_bp.route("/verification")
@login_required
@role_required(Role.ADMIN)
def verification():
    status = request.args.get("status", VerificationStatus.PENDING)
    shops = Shop.query.filter_by(verification_status=status).order_by(Shop.created_at.desc()).all()
    return render_template("admin/verification.html", shops=shops, status=status,
                            statuses=VerificationStatus.ALL)


@admin_bp.route("/verification/<int:shop_id>")
@login_required
@role_required(Role.ADMIN)
def verification_detail(shop_id):
    shop = Shop.query.get_or_404(shop_id)
    return render_template("admin/verification_detail.html", shop=shop)


@admin_bp.route("/verification/<int:shop_id>/document/<int:doc_id>")
@login_required
@role_required(Role.ADMIN)
def document(shop_id, doc_id):
    """The only route that can ever serve a verification document — it is
    stored outside static/ and requires an authenticated admin (doc #67/#80)."""
    doc = ShopDocument.query.filter_by(id=doc_id, shop_id=shop_id).first_or_404()
    folder = os.path.dirname(os.path.join(current_app.config["PRIVATE_UPLOAD_FOLDER"], doc.document_file))
    filename = os.path.basename(doc.document_file)
    return send_from_directory(folder, filename)


@admin_bp.route("/verification/<int:shop_id>/decide", methods=["POST"])
@login_required
@role_required(Role.ADMIN)
def verification_decide(shop_id):
    from datetime import datetime, timezone
    shop = Shop.query.get_or_404(shop_id)
    decision = request.form.get("decision")
    notes = request.form.get("notes", "").strip()

    if decision == "approve":
        shop.verification_status = VerificationStatus.APPROVED
        shop.verified_at = datetime.now(timezone.utc)
        notify(shop.owner_id, NotificationType.BUSINESS_VERIFIED,
               "Your business is verified", f"{shop.name} is now live on NearCart.")
        flash(f"{shop.name} approved.", "success")
    elif decision == "reject":
        shop.verification_status = VerificationStatus.REJECTED
        notify(shop.owner_id, NotificationType.BUSINESS_REJECTED,
               "Verification rejected", notes or "Your submission was rejected.")
        flash(f"{shop.name} rejected.", "success")
    elif decision == "correction":
        shop.verification_status = VerificationStatus.CORRECTION_REQUIRED
        notify(shop.owner_id, NotificationType.BUSINESS_REJECTED,
               "Correction needed", notes or "Please correct your submission.")
        flash(f"Correction requested for {shop.name}.", "success")
    else:
        abort(400)

    shop.verification_notes = notes
    db.session.commit()
    return redirect(url_for("admin.verification"))


@admin_bp.route("/businesses/<int:shop_id>/suspend", methods=["POST"])
@login_required
@role_required(Role.ADMIN)
def suspend_business(shop_id):
    shop = Shop.query.get_or_404(shop_id)
    shop.verification_status = VerificationStatus.SUSPENDED
    db.session.commit()
    flash(f"{shop.name} suspended.", "success")
    return redirect(url_for("admin.businesses"))


# ---------------------------------------------------------------- BUSINESSES / USERS

@admin_bp.route("/businesses")
@login_required
@role_required(Role.ADMIN)
def businesses():
    q = request.args.get("q", "").strip()
    query = Shop.query
    if q:
        query = query.filter(Shop.name.ilike(f"%{q}%"))
    shops = query.order_by(Shop.created_at.desc()).limit(200).all()
    return render_template("admin/businesses.html", shops=shops, q=q)


@admin_bp.route("/users")
@login_required
@role_required(Role.ADMIN)
def users():
    q = request.args.get("q", "").strip()
    query = User.query
    if q:
        query = query.filter(User.name.ilike(f"%{q}%"))
    people = query.order_by(User.created_at.desc()).limit(200).all()
    return render_template("admin/users.html", users=people, q=q)


@admin_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@login_required
@role_required(Role.ADMIN)
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot suspend your own account.", "error")
        return redirect(url_for("admin.users"))
    user.is_active_account = not user.is_active_account
    db.session.commit()
    return redirect(url_for("admin.users"))


# ---------------------------------------------------------------- REVIEWS / REPORTS

@admin_bp.route("/reviews")
@login_required
@role_required(Role.ADMIN)
def reviews():
    status = request.args.get("status", ReviewStatus.REPORTED)
    items = Review.query.filter_by(status=status).order_by(Review.created_at.desc()).all()
    return render_template("admin/reviews.html", reviews=items, status=status)


@admin_bp.route("/reviews/<int:review_id>/<action>", methods=["POST"])
@login_required
@role_required(Role.ADMIN)
def review_action(review_id, action):
    review = Review.query.get_or_404(review_id)
    if action == "remove":
        review.status = ReviewStatus.REMOVED
    elif action == "restore":
        review.status = ReviewStatus.ACTIVE
    else:
        abort(400)
    db.session.commit()
    return redirect(url_for("admin.reviews"))


@admin_bp.route("/reports")
@login_required
@role_required(Role.ADMIN)
def reports():
    status = request.args.get("status", ReportStatus.OPEN)
    items = Report.query.filter_by(status=status).order_by(Report.created_at.desc()).all()
    return render_template("admin/reports.html", reports=items, status=status)


@admin_bp.route("/reports/<int:report_id>/<action>", methods=["POST"])
@login_required
@role_required(Role.ADMIN)
def report_action(report_id, action):
    from datetime import datetime, timezone
    report = Report.query.get_or_404(report_id)
    if action == "resolve":
        report.status = ReportStatus.RESOLVED
        report.resolved_at = datetime.now(timezone.utc)
    elif action == "dismiss":
        report.status = ReportStatus.DISMISSED
        report.resolved_at = datetime.now(timezone.utc)
    elif action == "review":
        report.status = ReportStatus.UNDER_REVIEW
    else:
        abort(400)
    db.session.commit()
    return redirect(url_for("admin.reports"))


# ---------------------------------------------------------------- CATEGORIES

@admin_bp.route("/categories")
@login_required
@role_required(Role.ADMIN)
def categories():
    from app.models.category import Category
    items = Category.query.order_by(Category.type, Category.name).all()
    return render_template("admin/categories.html", categories=items)


# ---------------------------------------------------------------- DEMAND / SUPPLY REPORTS

@admin_bp.route("/insights")
@login_required
@role_required(Role.ADMIN)
def insights():
    report_type = request.args.get("type", "demand")
    start = request.args.get("start") or None
    end = request.args.get("end") or None

    if report_type == "supply":
        rows = analytics_report_service.supply_report(start=start, end=end)
    else:
        report_type = "demand"
        rows = analytics_report_service.demand_report(start=start, end=end)

    return render_template("admin/insights.html", rows=rows, report_type=report_type,
                            start=start or "", end=end or "")


@admin_bp.route("/insights/export/<fmt>")
@login_required
@role_required(Role.ADMIN)
def insights_export(fmt):
    report_type = request.args.get("type", "demand")
    start = request.args.get("start") or None
    end = request.args.get("end") or None

    if report_type == "supply":
        rows = analytics_report_service.supply_report(start=start, end=end)
    else:
        report_type = "demand"
        rows = analytics_report_service.demand_report(start=start, end=end)

    filename = f"nearcart-{report_type}-report"
    if fmt == "pdf":
        buffer = report_export_service.build_pdf(report_type, rows, start=start, end=end)
        return send_file(buffer, mimetype="application/pdf",
                          as_attachment=True, download_name=f"{filename}.pdf")
    elif fmt == "excel":
        buffer = report_export_service.build_excel(report_type, rows, start=start, end=end)
        return send_file(buffer, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                          as_attachment=True, download_name=f"{filename}.xlsx")
    abort(404)


@admin_bp.route("/categories/add", methods=["POST"])
@login_required
@role_required(Role.ADMIN)
def add_category():
    from app.models.category import Category
    import re
    name = request.form.get("name", "").strip()
    ctype = request.form.get("type", "SHOP")
    if name:
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        db.session.add(Category(name=name, slug=slug, type=ctype))
        db.session.commit()
        flash(f'Category "{name}" added.', "success")
    return redirect(url_for("admin.categories"))
