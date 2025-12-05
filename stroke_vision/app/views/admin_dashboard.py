from flask import Blueprint, jsonify, render_template, abort
from flask_login import login_required, current_user
from app.models.user import User
from app.utils.log_utils import log_activity, log_security
from datetime import datetime, timedelta

admin_dashboard_bp = Blueprint("admin_dashboard", __name__)


def _process_monthly_growth(users):
    """
    Groups users by Creation Date (Month/Year) for growth chart.
    Returns: {labels: ["Jan 2024", ...], data: [5, 12, ...]}
    """
    # Initialize last 6 months buckets
    today = datetime.now()
    buckets = {}
    labels = []
    
    # Generate labels for last 6 months
    for i in range(5, -1, -1):
        d = today - timedelta(days=i*30)
        key = d.strftime("%b %Y")
        buckets[key] = 0
        labels.append(key)
        
    for u in users:
        if u.created_at:
            key = u.created_at.strftime("%b %Y")
            if key in buckets:
                buckets[key] += 1
                
    return {"labels": labels, "data": [buckets[l] for l in labels]}


@admin_dashboard_bp.route("/admin/dashboard/view", methods=["GET"])
@login_required
def view_dashboard_partial():
    """Renders the HTML partial for the admin dashboard."""
    if current_user.role != "Admin":
         abort(403)
    return render_template("partials/admin_dashboard.html")


@admin_dashboard_bp.route("/admin/dashboard/api/stats", methods=["GET"])
@login_required
def get_admin_stats():
    """Returns analytics data for the admin dashboard."""
    if current_user.role != "Admin":
        return jsonify({"success": False, "message": "Access denied"}), 403
        
    try:
        users = User.query.all()
        
        # 1. KPIs
        total_users = len(users)
        locked_accounts = sum(1 for u in users if u.is_locked)
        admins = sum(1 for u in users if u.role == "Admin")
        doctors = sum(1 for u in users if u.role == "Doctor")
        nurses = sum(1 for u in users if u.role == "Nurse")
        
        # 2. Charts
        role_data = [admins, doctors, nurses] # Labels: Admin, Doctor, Nurse
        growth_data = _process_monthly_growth(users)
        
        log_activity(f"Admin viewed usage stats. Total users: {total_users}", level=2)
        
        return jsonify({
            "success": True,
            "kpis": {
                "total": total_users,
                "locked": locked_accounts,
                "admins": admins,
                "doctors": doctors,
                "nurses": nurses
            },
            "charts": {
                "roles": role_data,
                "growth": growth_data
            }
        })
        
    except Exception as e:
        log_security(f"Error generating admin stats: {e}", level=4)
        return jsonify({"success": False, "message": "Server error"}), 500
