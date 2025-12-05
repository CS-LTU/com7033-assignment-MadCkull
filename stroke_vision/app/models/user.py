# models/user.py
from app import db, bcrypt
from flask_login import UserMixin
from datetime import datetime


class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(6), nullable=False, default="Doctor")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def set_password(self, password):
        """Set password hash."""
        self.password = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        """Verify password."""
        return bcrypt.check_password_hash(self.password, password)
