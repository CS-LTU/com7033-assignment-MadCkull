# app/models/log.py
from mongoengine import Document, StringField, DateTimeField, IntField
from datetime import datetime


# --- Log Models ---


class ActivityLog(Document):
    """Logs for patient-data related actions."""

    # System Fields
    timestamp = DateTimeField(default=datetime.now)
    client_ip = StringField(required=True)
    client_os = StringField()

    # User Details
    user_name = StringField()
    user_role = StringField()

    # Log Content
    info = StringField(required=True)
    log_level = IntField(required=True, min_value=0, max_value=4)

    meta = {
        "collection": "activity_logs",
        "ordering": ["-timestamp"],
        "indexes": [
            ("log_level", "timestamp"),
        ],
    }


class SecurityLog(Document):
    """Logs for user and security-related actions."""

    # System Fields
    timestamp = DateTimeField(default=datetime.now)
    client_ip = StringField(required=True)
    client_os = StringField()

    # User Details
    user_name = StringField()
    user_role = StringField()

    # Log Content
    info = StringField(required=True)
    log_level = IntField(required=True, min_value=0, max_value=4)

    meta = {
        "collection": "security_logs",
        "ordering": ["-timestamp"],
        "indexes": [
            ("log_level", "timestamp"),
        ],
    }
