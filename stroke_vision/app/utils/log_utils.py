# app/utils/log_utils.py
from typing import Union
from flask import request
from flask_login import current_user
from app.models.log import (
    ActivityLog,
    SecurityLog,
)


def _get_client_context():
    """Internally extracts client IP and OS from the Flask request context."""

    # IP Address
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    client_ip = client_ip.split(",")[0].strip() if client_ip else "Unknown IP"

    # OS
    user_agent = request.user_agent
    client_os = "Unknown OS"
    if user_agent.platform:
        os_str = user_agent.platform.capitalize()
        if os_str in ["Windows", "Mac", "Linux"]:
            client_os = os_str
        elif os_str == "Ios":
            client_os = "iOS"
        else:
            client_os = os_str

    return {
        "client_ip": client_ip,
        "client_os": client_os,
    }


def _get_user_details():
    """Returns a dict with user name and role."""
    user = current_user
    if user and user.is_authenticated:
        return {"name": user.name, "role": user.role}
    return {"name": "Anonymous", "role": "System"}


def _log_base(LogModel: Union[ActivityLog, SecurityLog], info_message: str, level: int):
    """
    Internal function to handle common logic: context extraction and saving.
    """
    if not 0 <= level <= 4:
        print(
            f"--- LOGGING WARNING ---: Invalid log level '{level}'. Falling back to level 1."
        )
        level = 1

    try:
        client_context = _get_client_context()
        user_details = _get_user_details()

        log_entry = LogModel(
            info=info_message,
            log_level=level,
            client_ip=client_context["client_ip"],
            client_os=client_context["client_os"],
            user_name=user_details["name"],
            user_role=user_details["role"],
        )
        log_entry.save()

    except Exception as e:
        # Log failure safety
        print(
            f"--- LOGGING FAILED ---: Could not save log to {LogModel.__name__} (Level: {level}): {e}"
        )


def log_activity(info: str, level: int = 1):
    """
    Logs an action related to patient data (e.g., patient CRUD).

    :param info: The specific detail message.
    :param level: The priority level (0-4) for color-coding. Default is 1.
    """
    _log_base(ActivityLog, info, level)


def log_security(info: str, level: int = 1):
    """
    Logs an action related to user/security data (e.g., login, password change).

    :param info: The specific detail message.
    :param level: The priority level (0-4) for color-coding. Default is 1.
    """
    _log_base(SecurityLog, info, level)
