# app/views/auth.py
from flask import (
    Blueprint,
    request,
    render_template,
    redirect,
    url_for,
    flash,
)
from flask_login import login_user, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField
from wtforms.validators import DataRequired, Email, Length, Regexp
from app import db
from app.models.user import User

# NOTE: Ensure this path is correct based on your structure (e.g., app.utils.log_utils)
from app.utils.log_utils import log_security
import logging

logger = logging.getLogger(__name__)

auth = Blueprint("auth", __name__)

# Centralised flash categories
MSG = {
    "SUCCESS": "success",
    "ERROR": "danger",
    "WARNING": "warning",
    "INFO": "info",
}


class LoginForm(FlaskForm):
    email = StringField(
        "Email",
        validators=[
            DataRequired(),
            Email(message="Please enter a valid email address"),
        ],
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=8, message="Password must be at least 8 characters long"),
        ],
    )


class RegistrationForm(FlaskForm):
    name = StringField(
        "Name",
        validators=[
            DataRequired(),
            Regexp(
                r"^[A-Za-z]+( [A-Za-z]+){0,3}$",
                message="Name must contain only letters and maximum 3 spaces",
            ),
        ],
    )
    email = StringField(
        "Email",
        validators=[
            DataRequired(),
            Email(message="Please enter a valid email address"),
            Regexp(
                r"^[A-Za-z0-9._-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$",
                message="Email contains invalid characters",
            ),
        ],
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=8, message="Password must be at least 8 characters long"),
        ],
    )
    role = SelectField(
        "Role",
        choices=[("Doctor", "Doctor"), ("Nurse", "Nurse"), ("Admin", "Admin")],
        validators=[DataRequired()],
    )


@auth.route("/register", methods=["GET", "POST"])
def register():
    """Handle user registration."""
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    form = RegistrationForm()
    redirect_to = None

    if form.validate_on_submit():
        existing = User.query.filter_by(email=form.email.data).first()
        if existing:
            flash("Email already registered.", MSG["ERROR"])
            redirect_to = url_for("auth.register")
        else:
            if form.role.data == "Admin" and User.query.filter_by(role="Admin").first():
                flash("Only one Admin account is allowed.", MSG["ERROR"])
                redirect_to = url_for("auth.register")
            else:
                new_user = User(
                    name=form.name.data.strip(),
                    email=form.email.data.strip(),
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

                    flash("Registration successful! Please login.", MSG["SUCCESS"])
                    redirect_to = url_for("auth.login")
                except Exception:
                    db.session.rollback()
                    logger.exception(
                        "Registration failed for email=%s", form.email.data
                    )
                    flash("Registration failed. Please try again.", MSG["ERROR"])
                    redirect_to = url_for("auth.register")

    elif request.method == "POST" and form.errors:
        for field, errors in form.errors.items():
            for err in errors:
                flash(f"{field.capitalize()}: {err}", MSG["ERROR"])

    if redirect_to:
        return redirect(redirect_to)

    return render_template("auth/register.html", form=form)


@auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user and user.check_password(form.password.data):
            login_user(user, remember=True)

            log_security(f"Login successful for user '{user.email}'.", 3)

            flash("Login successful!", MSG["SUCCESS"])
            next_page = request.args.get("next")
            return redirect(next_page if next_page else url_for("home"))

        log_security(
            f"Login failure: Invalid credentials provided for email '{form.email.data}'.",
            4,
        )

        flash("Invalid email or password.", MSG["ERROR"])

    return render_template("auth/login.html", form=form)


@auth.route("/logout")
def logout():
    if current_user.is_authenticated:
        log_security("User logged out successfully.", 1)

    logout_user()
    flash("You have been logged out successfully.", MSG["INFO"])
    return redirect(url_for("auth.login"))
