# user_manager.py (MERGED & CORRECTED)
from flask import Blueprint, render_template, request, jsonify, abort
from flask_login import login_required, current_user
from app import db
from app.models.user import User  # Ensure this import is correct
import secrets
import string

# NOTE: Assuming your User model has 'check_password' and 'set_password' methods
# for secure password handling.

user_manager_bp = Blueprint("user_manager", __name__)


# =============================================================================
# 1. HELPER FUNCTIONS
# =============================================================================


def ensure_admin():
    """Helper to ensure current user is an Admin."""
    if current_user.role != "Admin":
        if (
            request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or request.is_json
        ):
            return jsonify(
                {"success": False, "message": "Admin privileges required"}
            ), 403
        abort(403)


# =============================================================================
# 2. VIEW ROUTES (User Settings and Admin Panel)
# =============================================================================


# NOTE: Added the view route for settings which was originally in settings.py
@user_manager_bp.route("/settings/view", methods=["GET"])
@login_required
def view_settings_panel():
    """Renders the settings HTML fragment for the current user."""
    return render_template("profile/settings.html", user=current_user)


@user_manager_bp.route("/admin/users/view", methods=["GET"])
@login_required
def view_users_panel():
    """Loads the user management panel fragment (Admin only)."""
    admin_check = ensure_admin()
    if admin_check:
        return admin_check

    return render_template("toolbar/user_manager.html")


# =============================================================================
# 3. CURRENT USER (SETTINGS) API ROUTES - MERGED FROM settings.py
# =============================================================================


@user_manager_bp.route("/settings/api/profile", methods=["PATCH"])
@login_required
def update_self_profile():
    """Logged-in user updates their own profile (name, email)."""
    data = request.get_json()
    new_name = data.get("name", "").strip()
    new_email = data.get("email", "").strip()

    user = User.query.get(current_user.id)

    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404

    # Handle updates...
    if new_name:
        user.name = new_name

    if new_email and new_email != user.email:
        if (
            User.query.filter(User.email == new_email)
            .filter(User.id != user.id)
            .first()
        ):
            return jsonify(
                {
                    "success": False,
                    "message": "Email already in use by another account.",
                }
            ), 409
        user.email = new_email

    if not new_name and not new_email:
        return jsonify({"success": False, "message": "No new data provided."}), 400

    try:
        db.session.commit()
        return jsonify({"success": True, "message": "Profile updated successfully."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@user_manager_bp.route("/settings/api/change_password", methods=["PATCH"])
@login_required
def change_self_password_api():
    """Logged-in user changes their password (requires current password)."""
    data = request.get_json()
    current_password = data.get("current_password")
    new_password = data.get("new_password")
    confirm_password = data.get("confirm_password")

    if not all([current_password, new_password, confirm_password]):
        return jsonify({"success": False, "message": "All fields are required."}), 400

    if new_password != confirm_password:
        return jsonify(
            {"success": False, "message": "New passwords do not match."}
        ), 400

    user = User.query.get(current_user.id)

    if not user.check_password(current_password):
        return jsonify(
            {"success": False, "message": "Incorrect current password."}
        ), 400

    try:
        # Uses the robust model method
        user.set_password(new_password)
        db.session.commit()
        return jsonify({"success": True, "message": "Password changed successfully."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


# =============================================================================
# 4. ADMIN API ROUTES (General User Management)
# =============================================================================


@user_manager_bp.route("/admin/api/users", methods=["GET"])
@login_required
def get_users_api():
    """Returns a list of all users and the current user's ID (Admin only)."""
    # ensure_admin() is called inside the function for admin check
    admin_check = ensure_admin()
    if admin_check:
        return admin_check

    users = User.query.order_by(User.created_at.desc()).all()

    users_data = []
    for u in users:
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


@user_manager_bp.route("/admin/api/users/update-email", methods=["PATCH"])
@login_required
def update_user_email():
    """Admin updates another user's email (Admin only)."""
    admin_check = ensure_admin()
    if admin_check:
        return admin_check

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
    """Admin updates another user's role (Admin only)."""
    admin_check = ensure_admin()
    if admin_check:
        return admin_check

    data = request.get_json()
    user_id = data.get("user_id")
    new_role = data.get("role", "").strip()

    if not user_id or not new_role:
        return jsonify(
            {"success": False, "message": "Missing user ID or new role."}
        ), 400

    if int(user_id) == current_user.id:
        return jsonify(
            {"success": False, "message": "You cannot change your own role."}
        ), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404

    if new_role not in ["Doctor", "Nurse"]:
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
    """Admin generates and sets a new random password for any user (Admin only)."""
    admin_check = ensure_admin()
    if admin_check:
        return admin_check

    user = User.query.get_or_404(user_id)

    # Generate a strong 12-character random password
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    new_password = "".join(secrets.choice(alphabet) for i in range(12))

    try:
        # FIX: Use the robust model method for password setting (set_password)
        # instead of manual hashing to ensure consistency and correctness.
        user.set_password(new_password)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"New password generated and set for user ID {user_id}.",
                "new_password": new_password,
            }
        )
    except Exception as e:
        db.session.rollback()
        # Log the error on the server side for debugging
        print(f"Database error on password reset: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


# =============================================================================
# 5. ADMIN API ROUTES (Admin Self Management)
# =============================================================================


@user_manager_bp.route("/admin/api/self/update-email", methods=["POST"])
@login_required
def update_self_email_api():
    admin_check = ensure_admin()
    if admin_check:
        return admin_check

    try:
        data = request.get_json() or {}
        new_email = (data.get("email") or "").strip()
        if not new_email:
            return jsonify({"success": False, "message": "Email is required."}), 400

        # basic validation
        if "@" not in new_email:
            return jsonify({"success": False, "message": "Invalid email."}), 400

        # check uniqueness excluding the current user
        if (
            User.query.filter(User.email == new_email)
            .filter(User.id != current_user.id)
            .first()
        ):
            return jsonify({"success": False, "message": "Email already in use."}), 409

        user = User.query.get(current_user.id)
        if not user:
            return jsonify({"success": False, "message": "User not found."}), 404

        user.email = new_email
        db.session.commit()

        # optionally: send verification email here

        return jsonify({"success": True, "message": "Email updated."})
    except Exception as e:
        db.session.rollback()
        # Log exact error on server for debugging
        print(f"Error updating self email for user {current_user.id}: {e}")
        return jsonify({"success": False, "message": "Internal server error."}), 500


@user_manager_bp.route("/admin/api/self/reset-password", methods=["POST"])
@login_required
def reset_self_password_api():
    """Admin resets their own password (generates a temporary password)."""
    admin_check = ensure_admin()
    if admin_check:
        return admin_check

    try:
        # Generate a temporary password for the admin
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        temp_password = "".join(secrets.choice(alphabet) for i in range(12))

        user = User.query.get(current_user.id)
        if not user:
            return jsonify({"success": False, "message": "User not found."}), 404

        user.set_password(temp_password)
        db.session.commit()

        # Return temp password so frontend can show it in the modal (same UX as other resets)
        return jsonify(
            {
                "success": True,
                "message": "Password reset initiated. A temporary password was set.",
                "temp_password": temp_password,
            }
        )
    except Exception as e:
        db.session.rollback()
        print(f"Database error on self password reset for user {current_user.id}: {e}")
        return jsonify({"success": False, "message": "Internal server error."}), 500
