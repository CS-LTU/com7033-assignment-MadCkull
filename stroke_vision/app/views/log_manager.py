from flask import Blueprint, render_template, jsonify, request, abort
from flask_login import login_required, current_user
from app.models.log import ActivityLog, SecurityLog

log_manager_bp = Blueprint("log_manager", __name__, url_prefix="/logs")

# Pagination settings
LOGS_PER_PAGE = 30


@log_manager_bp.route("/view/activity")
@login_required
def view_activity():
    """Renders the Activity View (Security Logs)."""
    if current_user.role != "Admin":
        abort(403)
    return render_template("partials/toolbar/activity.html")


@log_manager_bp.route("/view/changelog")
@login_required
def view_changelog():
    """Renders the Change Log View (Activity Logs)."""
    if current_user.role not in ["Admin", "Doctor"]:
        abort(403)
    return render_template("partials/toolbar/change_log.html")


@log_manager_bp.route("/api/activity", methods=["GET"])
@login_required
def get_activity_logs():
    """API to fetch Security Logs with pagination."""
    try:
        if current_user.role != "Admin":
            return jsonify({"error": "Admin privileges required."}), 403

        page = request.args.get("page", 1, type=int)
        skip = (page - 1) * LOGS_PER_PAGE

        # Get total count for has_more calculation
        total = SecurityLog.objects.count()
        logs = SecurityLog.objects.order_by("-timestamp").skip(skip).limit(LOGS_PER_PAGE)

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
        
        has_more = (skip + len(data)) < total
        
        return jsonify({
            "logs": data,
            "page": page,
            "has_more": has_more
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@log_manager_bp.route("/api/changelog", methods=["GET"])
@login_required
def get_change_logs():
    """API to fetch Activity Logs with pagination."""
    try:
        if current_user.role not in ["Admin", "Doctor"]:
            return jsonify({"error": "Access denied."}), 403

        page = request.args.get("page", 1, type=int)
        skip = (page - 1) * LOGS_PER_PAGE

        total = ActivityLog.objects.count()
        logs = ActivityLog.objects.order_by("-timestamp").skip(skip).limit(LOGS_PER_PAGE)

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
        
        has_more = (skip + len(data)) < total
        
        return jsonify({
            "logs": data,
            "page": page,
            "has_more": has_more
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
