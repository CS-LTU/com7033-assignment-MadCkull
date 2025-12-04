# app/__init__.py
import os
from dotenv import load_dotenv
from flask import Flask, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_login import LoginManager
from mongoengine import connect
from flask_wtf.csrf import CSRFProtect, CSRFError
from flask_wtf.csrf import generate_csrf
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Logging
from app.utils.log_utils import log_security

# Initialize extensions
db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)

# Load environment variables from .env file
load_dotenv()


def create_app():
    app = Flask(__name__)

    # Configurations
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("SQLITE_DATABASE_URI")
    app.config["MONGO_URI"] = os.getenv("MONGO_URI")

    # Security Configurations
    app.config["ADMIN_INVITE_CODE"] = os.getenv("ADMIN_INVITE_CODE")
    app.config["ACCOUNT_LOCKOUT_ATTEMPTS"] = int(os.getenv("ACCOUNT_LOCKOUT_ATTEMPTS", 5))
    app.config["ACCOUNT_LOCKOUT_PERIOD_SECONDS"] = int(os.getenv("ACCOUNT_LOCKOUT_PERIOD_SECONDS", 900))
    app.config["RATELIMIT_STRATEGY"] = "fixed-window"
    app.config["RATELIMIT_STORAGE_URI"] = "memory://"

    # CSRF specific configurations
    app.config["WTF_CSRF_ENABLED"] = True
    app.config["WTF_CSRF_TIME_LIMIT"] = 3600  # 1 hour
    app.config["WTF_CSRF_SSL_STRICT"] = True
    app.config["WTF_CSRF_CHECK_DEFAULT"] = True

    # Initialize extensions with app
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # Login Manager
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    # Database (connect before importing blueprints that require indexes)
    connect(host=app.config["MONGO_URI"])

    # Blueprints
    from app.views.auth import auth

    app.register_blueprint(auth, url_prefix="/auth")

    from app.views.patient_manager import patient_bp

    app.register_blueprint(patient_bp, url_prefix="/patient")

    from app.views.search_manager import search_bp

    app.register_blueprint(search_bp)

    from app.views.user_manager import user_manager_bp

    app.register_blueprint(user_manager_bp)

    from app.views.dashboard import dashboard_bp

    app.register_blueprint(dashboard_bp)

    from app.views.log_manager import log_manager_bp

    app.register_blueprint(log_manager_bp)

    from app.views.admin_dashboard import admin_dashboard_bp

    app.register_blueprint(admin_dashboard_bp)



    # Error Handlers
    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        try:
            log_security(f"CSRF token missing/invalid - {str(e)}", level=2)
        except Exception:
            pass

        return jsonify(
            {"error": "CSRF token missing or invalid", "message": str(e)}
        ), 400

    @app.errorhandler(400)
    def handle_bad_request(e):
        try:
            log_security(f"Bad Request - {str(e)}", level=2)
        except Exception:
            pass

        return jsonify({"error": "Bad Request", "message": str(e)}), 400

    @app.errorhandler(500)
    def handle_server_error(e):
        try:
            log_security(
                "Internal Server Error: An unexpected error occurred. "
                f"Exception: {str(e)}",
                level=3,
            )
        except Exception:
            pass

        return jsonify(
            {
                "error": "Internal Server Error",
                "message": "An unexpected error occurred",
            }
        ), 500

    # CSRF Header
    @app.after_request
    def add_csrf_header(response):
        if "text/html" in response.headers.get("Content-Type", ""):
            response.set_cookie(
                "csrf_token",
                generate_csrf(),
                secure=True,
                samesite="Strict",
                httponly=True,
            )
        return response

    # Global Session Validation (AuthShield)
    from app.security.auth_shield import AuthShield
    @app.before_request
    def check_session_security():
        return AuthShield.validate_session()

    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User

        user = User.query.get(int(user_id))
        if user is None:
            try:
                log_security(
                    f"User loader failed to find user with id={user_id}", level=2
                )
            except Exception:
                pass
        return user

    @app.route("/")
    def home():
        return render_template("home.html")

    return app
