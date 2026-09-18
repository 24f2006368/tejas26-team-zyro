from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db
from app.constants import Role
from app.models.user import User

auth_bp = Blueprint("auth", __name__, url_prefix="")


def _redirect_for_role(user):
    if user.role == Role.SHOPKEEPER:
        return redirect(url_for("shopkeeper.home"))
    if user.role == Role.ADMIN:
        return redirect(url_for("admin.overview"))
    return redirect(url_for("customer.dashboard"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return _redirect_for_role(current_user)

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter(
            (User.email == identifier) | (User.phone == identifier)
        ).first()

        if not user or not user.check_password(password):
            flash("Invalid email/phone or password.", "error")
            return render_template("auth/login.html")

        if not user.is_active_account:
            flash("This account has been suspended. Contact support.", "error")
            return render_template("auth/login.html")

        login_user(user)
        return _redirect_for_role(user)

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("main.home"))


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    """Customer registration only — kept short per doc #9."""
    if current_user.is_authenticated:
        return _redirect_for_role(current_user)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip() or None
        phone = request.form.get("phone", "").strip() or None
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        address = request.form.get("address", "").strip() or None

        errors = []
        if not name:
            errors.append("Full name is required.")
        if not email and not phone:
            errors.append("Provide an email or phone number.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if password != confirm_password:
            errors.append("Passwords do not match.")
        if email and User.query.filter_by(email=email).first():
            errors.append("An account with this email already exists.")
        if phone and User.query.filter_by(phone=phone).first():
            errors.append("An account with this phone number already exists.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("auth/signup.html", form=request.form)

        user = User(name=name, email=email, phone=phone, address=address, role=Role.CUSTOMER)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash(f"Welcome to NearCart, {user.name.split()[0]}!", "success")
        return redirect(url_for("customer.dashboard"))

    return render_template("auth/signup.html", form={})
