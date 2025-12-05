# app/models/user.py
import datetime
from app import db, bcrypt
from flask_login import UserMixin
from flask import current_app
from itsdangerous import URLSafeTimedSerializer

class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)  # store hashed password
    role = db.Column(db.String(20), nullable=False, default="Doctor")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)

    # Lockout related fields
    failed_login_attempts = db.Column(db.Integer, nullable=False, default=0)
    last_failed_login = db.Column(db.DateTime, nullable=True)
    is_locked = db.Column(db.Boolean, nullable=False, default=False)
    locked_at = db.Column(db.DateTime, nullable=True)

    def set_password(self, password: str):
        """Hash and store password."""
        self.password = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password: str) -> bool:
        """Verify password against stored hash."""
        return bcrypt.check_password_hash(self.password, password)

    # ---------- Lockout helpers ----------
    def increment_failed_attempts(self, commit: bool = True):
        """Increase failed attempt counter and set last_failed_login timestamp."""
        self.failed_login_attempts = (self.failed_login_attempts or 0) + 1
        self.last_failed_login = datetime.datetime.utcnow()
        if commit:
            db.session.add(self)
            db.session.commit()

    def reset_failed_attempts(self, commit: bool = True):
        """Reset failed attempt counter."""
        self.failed_login_attempts = 0
        self.last_failed_login = None
        if commit:
            db.session.add(self)
            db.session.commit()

    def lock(self, commit: bool = True):
        """Lock account immediately."""
        self.is_locked = True
        self.locked_at = datetime.datetime.utcnow()
        if commit:
            db.session.add(self)
            db.session.commit()

    def unlock(self, commit: bool = True):
        """Unlock account and reset counters."""
        self.is_locked = False
        self.locked_at = None
        self.reset_failed_attempts(commit=False)
        if commit:
            db.session.add(self)
            db.session.commit()

    @property
    def locked_for_seconds(self) -> int:
        """Return seconds since lock; 0 if not locked."""
        if not self.is_locked or not self.locked_at:
            return 0
        delta = datetime.datetime.utcnow() - self.locked_at
        return int(delta.total_seconds())

    # ---------- Token helpers (for email unlock / password reset) ----------
    def _get_serializer(self):
        secret = current_app.config["SECRET_KEY"]
        return URLSafeTimedSerializer(secret)

    def generate_unlock_token(self, purpose: str = "unlock", expires_sec: int = 3600):
        """
        Create a time-limited token. Use purpose if you want to distinguish token types.
        expires_sec is advisory when verifying using loads(..., max_age=...).
        """
        s = self._get_serializer()
        return s.dumps({"user_id": self.id, "purpose": purpose})

    @staticmethod
    def verify_token(token: str, max_age: int = 3600, expected_purpose: str = "unlock"):
        s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        try:
            data = s.loads(token, max_age=max_age)
        except Exception:
            return None
        if data.get("purpose") != expected_purpose:
            return None
        user_id = data.get("user_id")
        return User.query.get(user_id)
