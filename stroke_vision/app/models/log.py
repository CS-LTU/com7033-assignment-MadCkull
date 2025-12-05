# app/models/log.py
from mongoengine import Document, StringField, DateTimeField, IntField
from datetime import datetime


# --- BASE LOG MODELS (Separate Collections) ---


class ActivityLog(Document):
    """Logs for patient-data related actions."""

    # Fixed fields (handled by log_utils.py)
    timestamp = DateTimeField(default=datetime.now)
    client_ip = StringField(required=True)
    client_os = StringField()

    # User context
    user_name = StringField()
    user_role = StringField()

    # User-defined fields
    info = StringField(required=True)
    log_level = IntField(required=True, min_value=0, max_value=4)

    meta = {
        "collection": "activity_logs",
        "ordering": ["-timestamp"],
        "indexes": [
            ("log_level", "timestamp"),  # For filtering and sorting
        ],
    }


class SecurityLog(Document):
    """Logs for user and security-related actions."""

    # Fixed fields (handled by log_utils.py)
    timestamp = DateTimeField(default=datetime.now)
    client_ip = StringField(required=True)
    client_os = StringField()

    # User context
    user_name = StringField()
    user_role = StringField()

    # User-defined fields
    info = StringField(required=True)
    log_level = IntField(required=True, min_value=0, max_value=4)

    meta = {
        "collection": "security_logs",
        "ordering": ["-timestamp"],
        "indexes": [
            ("log_level", "timestamp"),  # For filtering and sorting
        ],
    }
