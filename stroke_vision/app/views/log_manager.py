from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required
from app.models.log import ActivityLog, SecurityLog

log_manager_bp = Blueprint("log_manager", __name__, url_prefix="/logs")


@log_manager_bp.route("/view/activity")
@login_required
def view_activity():
    """Renders the Activity View (Security Logs)."""
    return render_template("partials/toolbar/activity.html")


@log_manager_bp.route("/view/changelog")
@login_required
def view_changelog():
    """Renders the Change Log View (Activity Logs)."""
    return render_template("partials/toolbar/change_log.html")


@log_manager_bp.route("/api/activity", methods=["GET"])
@login_required
def get_activity_logs():
    """
    API to fetch Security Logs (User Logins, etc).
    Mapped to 'Activity' view in UI.
    """
    try:
        # Default sort by timestamp desc, limit 100 for performance
        logs = SecurityLog.objects.order_by("-timestamp").limit(100)

        data = [
            {
                "timestamp": log.timestamp.isoformat(),
                "info": log.info,
                "client_ip": log.client_ip,
                "client_os": log.client_os,
                "user_name": getattr(log, "user_name", None),
                "user_role": getattr(log, "user_role", None),
                "log_level": log.log_level,
            }
            for log in logs
        ]
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@log_manager_bp.route("/api/changelog", methods=["GET"])
@login_required
def get_change_logs():
    """
    API to fetch Activity Logs (Patient Data Changes).
    Mapped to 'Change Log' view in UI.
    """
    try:
        # Default sort by timestamp desc, limit 100
        logs = ActivityLog.objects.order_by("-timestamp").limit(100)

        data = [
            {
                "timestamp": log.timestamp.isoformat(),
                "info": log.info,
                "client_ip": log.client_ip,
                "client_os": log.client_os,
                "user_name": getattr(log, "user_name", None),
                "user_role": getattr(log, "user_role", None),
                "log_level": log.log_level,
            }
            for log in logs
        ]
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
