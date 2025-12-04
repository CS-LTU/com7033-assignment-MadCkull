# app/views/auth.py
from flask import (
    Blueprint,
    request,
    render_template,
    redirect,
    url_for,
    flash,
    current_app,
)
from flask_login import login_user, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    SelectField,
    BooleanField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    Length,
    Regexp,
    ValidationError,
    Optional,
)
from urllib.parse import urlparse, urljoin
from sqlalchemy.exc import IntegrityError
from app import db
from app.models.user import User
from app import db, limiter
from app.utils.log_utils import log_security
import logging
import os
import datetime

logger = logging.getLogger(__name__)

auth = Blueprint("auth", __name__)

# Centralised flash categories used by UI notification popup
MSG = {
    "SUCCESS": "success",
    "ERROR": "danger",
    "WARNING": "warning",
    "INFO": "info",
}

# Small local list of common weak passwords.
COMMON_PASSWORDS = {
    "password",
    "123456",
    "12345678",
    "123456789",
    "qwerty",
    "abc123",
    "password1",
    "admin",
    "letmein",
    "welcome",
}


def is_safe_url(target):
    """Prevent open redirect attacks by ensuring 'next' is local."""
    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))
    return (redirect_url.scheme in ("http", "https")) and (host_url.netloc == redirect_url.netloc)


def _clean_string(value):
    """Normalise / strip string fields; return None if empty after strip."""
    if value is None:
        return None
    if isinstance(value, str):
        v = value.strip()
        return v if v != "" else None
    return value


def clean_form_str_fields(form):
    """Strip whitespace for all string-like fields on the form before use."""
    for name, field in form._fields.items():
        if hasattr(field, "data") and isinstance(field.data, str):
            field.data = field.data.strip()


def password_complexity(form, field):
    """WTForms custom validator enforcing password rules."""
    pw = field.data or ""
    # Basic length guard (it's already also enforced by Length)
    if len(pw) < 8:
        raise ValidationError("Password must be at least 8 characters long.")

    conditions = [
        any(c.islower() for c in pw),
        any(c.isupper() for c in pw),
        any(c.isdigit() for c in pw),
        any(not c.isalnum() for c in pw),
    ]
    if not all(conditions):
        raise ValidationError(
            "Password must include Upper/Lowercase, a Number and a Special Character."
        )
    if pw.lower() in COMMON_PASSWORDS:
        raise ValidationError("That password is too common. Choose something harder to guess.")


# Forms
class LoginForm(FlaskForm):
    email = StringField(
        "Email",
        validators=[DataRequired(message="Email is required"), Email(message="Please enter a valid email address")],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(message="Password is required"), Length(min=8)],
    )
    remember = BooleanField("Remember me", default=False)


class RegistrationForm(FlaskForm):
    # Accept letters, spaces, hyphens, apostrophes, up to 5 name parts
    name = StringField(
        "Name",
        validators=[
            DataRequired(message="Name is required"),
            Regexp(
                r"^[A-Za-zÀ-ÖØ-öø-ÿ'’\-.]+(?:[ \t]+[A-Za-zÀ-ÖØ-öø-ÿ'’\-.]+){0,4}$",
                message="Please enter a valid name",
            ),
        ],
    )
    email = StringField(
        "Email",
        validators=[DataRequired(message="Email is required"), Email(message="Please enter a valid email address")],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(message="Password is required"), password_complexity],
    )
    role = SelectField(
        "Role",
        choices=[("Doctor", "Doctor"), ("Nurse", "Nurse"), ("Admin", "Admin")],
        validators=[DataRequired(message="Role is required")],
    )
    # Optional admin invite code (Set in APP config (.env file) ADMIN_INVITE_CODE)
    admin_code = StringField("Invite Code", validators=[Optional()])


# Routes
@auth.route("/register", methods=["GET", "POST"])
def register():
    """Handle user registration with safer checks and informative flash messages."""
    if current_user.is_authenticated:
        flash("You are already logged in.", MSG["INFO"])
        return redirect(url_for("home"))

    form = RegistrationForm()

    if form.validate_on_submit():
        # Normalize inputs
        clean_form_str_fields(form)
        name = _clean_string(form.name.data)
        email = _clean_string(form.email.data)
        if email:
            email = email.lower()  # This ensures uniqueness check is case-insensitive

        # Backend enforcement: Admin creation requires invite code or no existing admin
        if form.role.data == "Admin":
            configured_code = current_app.config.get("ADMIN_INVITE_CODE")
            # If a configured invite code exists, require it; else allow only if no Admin exists
            if configured_code:
                provided = _clean_string(form.admin_code.data)
                if not provided or provided != configured_code:
                    flash("Admin registration requires a valid invite code.", MSG["ERROR"])
                    log_security(f"Unauthorized Admin registration attempt for email '{email}'.", 4)
                    return redirect(url_for("auth.register"))
            else:
                existing_admin = User.query.filter_by(role="Admin").first()
                if existing_admin:
                    flash("Admin account already exists.", MSG["ERROR"])
                    log_security(f"Attempt to create second Admin by email '{email}'.", 4)
                    return redirect(url_for("auth.register"))

        # Check duplicate email with case-insensitive comparison
        existing = User.query.filter(db.func.lower(User.email) == email).first()
        if existing:
            flash("This email is already registered.", MSG["ERROR"])
            return redirect(url_for("auth.register"))

        # Create user
        new_user = User(
            name=name,
            email=email,
            role=form.role.data,
        )
        new_user.set_password(form.password.data)

        try:
            db.session.add(new_user)
            db.session.commit()
            log_security(
                f"Registered new user '{new_user.name}' ({new_user.email}) with role '{new_user.role}'.",
                3,
            )
            return redirect(url_for("auth.login"))
        except IntegrityError as e:
            db.session.rollback()
            logger.exception("Registration DB integrity error for email=%s", email)
            flash("Registration failed. Please try again.", MSG["ERROR"])
            return redirect(url_for("auth.register"))
        except Exception:
            db.session.rollback()
            logger.exception("Registration failed for email=%s", email)
            flash("Registration failed.", MSG["ERROR"])
            return redirect(url_for("auth.register"))

    # If POST with errors, flash them back to the UI (field label + specific message)
    elif request.method == "POST" and form.errors:
        for field_name, errors in form.errors.items():
            field_label = getattr(form, field_name).label.text if hasattr(form, field_name) else field_name
            for err in errors:
                flash(f"{field_label}: {err}", MSG["ERROR"])

    return render_template("auth/register.html", form=form)


@auth.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    """Login with safe redirect, logging, and optional remember."""
    if current_user.is_authenticated:
        flash("You are already logged in.", MSG["INFO"])
        return redirect(url_for("home"))

    form = LoginForm()

    if form.validate_on_submit():
        clean_form_str_fields(form)
        email = _clean_string(form.email.data)
        if email:
            email = email.lower()

        user = User.query.filter(db.func.lower(User.email) == email).first()

        # Config variables
        max_attempts = current_app.config.get("ACCOUNT_LOCKOUT_ATTEMPTS", 5)
        lock_period = current_app.config.get("ACCOUNT_LOCKOUT_PERIOD_SECONDS", 900)

        # 1. Check if user is locked out
        if user and user.is_locked:
            # Auto-unlock check
            if user.locked_for_seconds >= lock_period:
                user.unlock()
                logger.info("Auto-unlocked user %s after lockout period", user.email)
            else:
                # Still locked
                flash(
                    "Account locked. Contact an admin to unlock.",
                    MSG["ERROR"],
                )
                return render_template("auth/login.html", form=form)

        # 2. Check credentials
        if user and user.check_password(form.password.data):
            # Success
            user.reset_failed_attempts()
            login_user(user, remember=form.remember.data)
            log_security(f"Login successful for user '{user.email}'.", 3)
            # flash("Login successful.", MSG["SUCCESS"])

            next_page = request.args.get("next")
            if next_page and is_safe_url(next_page):
                return redirect(next_page)
            return redirect(url_for("home"))
        
        # 3. Failure (Invalid password or User not found)
        # Avoid user enumeration: show same message for both cases
        if user:
            user.increment_failed_attempts()
            if user.failed_login_attempts >= max_attempts:
                user.lock()
                flash(
                    "Account locked due to failed attempts.",
                    MSG["ERROR"],
                )
                log_security(f"Account locked for user '{user.email}'.", 4)
                return render_template("auth/login.html", form=form)

        log_security(
            f"Login failure: Invalid credentials provided for email '{email}'.",
            4,
        )
        flash("Invalid email or password.", MSG["ERROR"])

    elif request.method == "POST" and form.errors:
        for field_name, errors in form.errors.items():
            field_label = getattr(form, field_name).label.text if hasattr(form, field_name) else field_name
            for err in errors:
                flash(f"{field_label}: {err}", MSG["ERROR"])

    return render_template("auth/login.html", form=form)


@auth.route("/logout")
def logout():
    if current_user.is_authenticated:
        log_security(f"User '{getattr(current_user, 'email', 'unknown')}' logged out.", 1)

    logout_user()
    flash("You have been logged out.", MSG["INFO"])
    return redirect(url_for("auth.login"))
