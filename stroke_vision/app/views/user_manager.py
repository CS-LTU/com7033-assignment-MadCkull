from flask import Blueprint, render_template, request, jsonify, abort
from flask_login import login_required, current_user
from app import db
from app.models.user import User
from werkzeug.security import generate_password_hash
import secrets
import string

user_manager_bp = Blueprint("user_manager", __name__)


def ensure_admin():
    """Helper to ensure current user is an Admin."""
    if current_user.role != "Admin":
        # Check if the request is an API call for a proper JSON response
        if (
            request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or request.is_json
        ):
            return jsonify(
                {"success": False, "message": "Admin privileges required"}
            ), 403
        abort(403)  # Forbidden for regular views


# --- View Route ---
@user_manager_bp.route("/admin/users/view", methods=["GET"])
@login_required
def view_users_panel():
    """Loads the user management panel fragment."""
    ensure_admin()
    return render_template("toolbar/user_manager.html")


# --- API Routes ---


@user_manager_bp.route("/admin/api/users", methods=["GET"])
@login_required
def get_users_api():
    """Returns a list of all users and the current user's ID."""
    ensure_admin()
    users = User.query.order_by(User.created_at.desc()).all()

    users_data = []
    for u in users:
        # Use window.formatDate for client-side formatting where possible,
        # but format for basic display consistency.
        created_at = u.created_at.strftime("%Y-%m-%d") if u.created_at else "N/A"

        users_data.append(
            {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "role": u.role,
                "created_at": created_at,
            }
        )

    return jsonify(
        {"success": True, "current_user_id": current_user.id, "users": users_data}
    )


# --- GENERAL USER MANAGEMENT (Requires Admin Role) ---


@user_manager_bp.route("/admin/api/users/update-email", methods=["PATCH"])
@login_required
def update_user_email():
    """Admin updates another user's email."""
    ensure_admin()
    data = request.get_json()
    user_id = data.get("user_id")
    new_email = data.get("email", "").strip()

    if not user_id or not new_email:
        return jsonify(
            {"success": False, "message": "Missing user ID or new email."}
        ), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404

    # Check for email conflict
    if User.query.filter(User.email == new_email).filter(User.id != user_id).first():
        return jsonify(
            {"success": False, "message": "Email already in use by another account."}
        ), 409

    try:
        user.email = new_email
        db.session.commit()
        return jsonify({"success": True, "message": "User email updated."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@user_manager_bp.route("/admin/api/users/update-role", methods=["PATCH"])
@login_required
def update_user_role():
    """Admin updates another user's role."""
    ensure_admin()
    data = request.get_json()
    user_id = data.get("user_id")
    new_role = data.get("role", "").strip()

    if not user_id or not new_role:
        return jsonify(
            {"success": False, "message": "Missing user ID or new role."}
        ), 400

    if user_id == current_user.id:
        return jsonify(
            {"success": False, "message": "You cannot change your own role."}
        ), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404

    # Simple validation for allowed roles (adjust as needed)
    if new_role not in ["Admin", "Editor", "Viewer"]:
        return jsonify({"success": False, "message": "Invalid role specified."}), 400

    try:
        user.role = new_role
        db.session.commit()
        return jsonify({"success": True, "message": "User role updated."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@user_manager_bp.route(
    "/admin/api/users/reset-password/<int:user_id>", methods=["POST"]
)
@login_required
def reset_password_api(user_id):
    """Admin generates and sets a new random password for any user."""
    ensure_admin()
    user = User.query.get_or_404(user_id)

    # Generate a strong 12-character random password
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    new_password = "".join(secrets.choice(alphabet) for i in range(12))

    try:
        # NOTE: This should ideally trigger an email notification,
        # but for this environment, we return the password directly.
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": "New password generated and set.",
                "new_password": new_password,
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


# --- ADMIN SELF MANAGEMENT ---


@user_manager_bp.route("/admin/api/self/update-email", methods=["PATCH"])
@login_required
def update_self_email():
    """Admin updates their own email."""
    ensure_admin()
    data = request.get_json()
    new_email = data.get("email", "").strip()

    if not new_email:
        return jsonify({"success": False, "message": "New email is required."}), 400

    # Check for email conflict
    if (
        User.query.filter(User.email == new_email)
        .filter(User.id != current_user.id)
        .first()
    ):
        return jsonify(
            {"success": False, "message": "Email already in use by another account."}
        ), 409

    try:
        current_user.email = new_email
        db.session.commit()
        return jsonify({"success": True, "message": "Your email has been updated."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@user_manager_bp.route("/admin/api/self/reset-password", methods=["POST"])
@login_required
def reset_self_password():
    """Admin resets their own password (usually via email link, but here we provide a temporary password/link placeholder)."""
    ensure_admin()

    # In a real app, this would trigger a password reset flow via email.
    # For simplicity and security in this environment, we'll confirm the intent.
    try:
        # Generate a temporary password for the admin (This is a simplified/insecure model)
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        temp_password = "".join(secrets.choice(alphabet) for i in range(12))

        current_user.password_hash = generate_password_hash(temp_password)
        db.session.commit()

        # NOTE: Returning the password directly is insecure.
        # A real application should send an email. We simulate success here.
        return jsonify(
            {
                "success": True,
                "message": "Password reset initiated. A temporary password was set. Please check your email (simulated).",
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
