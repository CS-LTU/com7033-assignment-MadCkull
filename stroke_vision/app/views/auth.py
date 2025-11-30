# app/views/auth.py
from flask import (
    Blueprint,
    request,
    render_template,
    redirect,
    url_for,
    flash,
    jsonify,
    get_flashed_messages,
)
from flask_login import login_user, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField
from wtforms.validators import DataRequired, Email, Length, Regexp, ValidationError
from app import db, bcrypt
from app.models.user import User
import json

import pyperclip

import logging


auth = Blueprint("auth", __name__)


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
            Length(min=6, message="Password must be at least 8 characters long"),
        ],
    )


class RegistrationForm(FlaskForm):
    name = StringField(
        "Name",
        validators=[
            DataRequired(),
            Regexp(
                r"^[A-Za-z]+( [A-Za-z]+){0,3}$",
                message="Name must contain only letters and max 3 spaces",
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
        choices=[("Admin", "Admin"), ("Doctor", "Doctor"), ("Nurse", "Nurse")],
        validators=[DataRequired()],
    )


@auth.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if email already exists
        if User.query.filter_by(email=form.email.data).first():
            flash("Email already registered", "danger")
            return redirect(url_for("auth.register"))

        # Enforce only 1 Admin
        if form.role.data == "Admin" and User.query.filter_by(role="Admin").first():
            flash("Only one Admin account is allowed.", "danger")
            return redirect(url_for("auth.register"))

        # Create new user
        new_user = User(name=form.name.data, email=form.email.data, role=form.role.data)
        new_user.set_password(form.password.data)

        try:
            db.session.add(new_user)
            db.session.commit()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("auth.login"))
        except Exception as e:
            db.session.rollback()
            flash(json.dumps(f"Registration failed: {str(e)}"), "danger")
            return redirect(url_for("auth.register"))

    messages = get_flashed_messages(with_categories=True)
    pyperclip.copy(str(messages))
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
            next_page = request.args.get("next")
            flash("Login successful!", "success")
            return redirect(next_page if next_page else url_for("home"))

        flash("Invalid email or password", "danger")

    return render_template("auth/login.html", form=form)


@auth.route("/logout")
def logout():
    logout_user()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("auth.login"))
