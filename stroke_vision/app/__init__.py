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

# Logging
from app.utils.log_utils import log_security

# Initialize extensions
db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()
login_manager = LoginManager()
csrf = CSRFProtect()

# Load environment variables from .env file
load_dotenv()


def create_app():
    app = Flask(__name__)

    # Configurations
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("SQLITE_DATABASE_URI")
    app.config["MONGO_URI"] = os.getenv("MONGO_URI")

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

    # Set login view
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    # Import and register blueprints
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

    # Connect to MongoDB
    connect(host=app.config["MONGO_URI"])

    # Error handlers
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

    # Add CSRF token to response headers
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
