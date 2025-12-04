# user_manager.py (Refactored for AuthShield)
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.user import User
import secrets
import string

# Logging utilities
from app.utils.log_utils import log_security, log_activity

# Security Modules
from app.security.auth_shield import AuthShield
from app.security.input_sanitizer import InputSanitizer

user_manager_bp = Blueprint("user_manager", __name__)

# =============================================================================
# 2. VIEW ROUTES (User Settings and Admin Panel)
# =============================================================================

@user_manager_bp.route("/settings/view", methods=["GET"])
@login_required
def view_settings_panel():
    """Renders the settings HTML fragment for the current user."""
    # Log that user viewed their settings (info)
    try:
        log_security("Viewed settings.", level=1)
    except Exception:
        pass
    return render_template("profile/settings.html", user=current_user)


@user_manager_bp.route("/admin/users/view", methods=["GET"])
@login_required
@AuthShield.require_role(["Admin"])
def view_users_panel():
    """Loads the user management panel fragment (Admin only)."""
    # Log that admin opened the user management UI
    try:
        log_security("Opened user manager.", level=1)
    except Exception:
        pass
    return render_template("toolbar/user_manager.html")


# =============================================================================
# 3. CURRENT USER (SETTINGS) API ROUTES
# =============================================================================

@user_manager_bp.route("/settings/api/profile", methods=["PATCH"])
@login_required
@AuthShield.secure_transaction
def update_self_profile():
    """Logged-in user updates their own profile (name, email)."""
    # Sanitize inputs
    data = InputSanitizer.clean_form_data(request.get_json())
    new_name = data.get("name", "")
    new_email = data.get("email", "")

    user = User.query.get(current_user.id)
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404

    changed_fields = []
    old_email = user.email

    # Handle updates
    if new_name:
        if new_name != user.name:
            changed_fields.append("name")
        user.name = new_name

    if new_email and new_email != user.email:
        if User.query.filter(User.email == new_email).filter(User.id != user.id).first():
            return jsonify({"success": False, "message": "Email already in use by another account."}), 409
        
        changed_fields.append("email")
        user.email = new_email

    if not new_name and not new_email:
        return jsonify({"success": False, "message": "No new data provided."}), 400

    # Logging success
    try:
        details = ", ".join(changed_fields) if changed_fields else "none"
        extra = ""
        if "email" in changed_fields:
            extra = f" Email changed from {old_email} -> {new_email}."
        log_security(f"Updated profile details.{extra}", level=1)
    except Exception:
        pass

    return jsonify({"success": True, "message": "Profile updated."})


@user_manager_bp.route("/settings/api/change_password", methods=["PATCH"])
@login_required
@AuthShield.secure_transaction
def change_self_password_api():
    """Logged-in user changes their password."""
    data = request.get_json()
    current_password = data.get("current_password")
    new_password = data.get("new_password")
    confirm_password = data.get("confirm_password")

    if not all([current_password, new_password, confirm_password]):
        return jsonify({"success": False, "message": "All fields are required."}), 400

    if new_password != confirm_password:
        return jsonify({"success": False, "message": "New passwords do not match."}), 400

    user = User.query.get(current_user.id)
    if not user.check_password(current_password):
        # We can log this locally but return generic message
        try:
            log_security("Password change failed: incorrect current password.", level=2)
        except Exception:
            pass
        return jsonify({"success": False, "message": "Incorrect current password."}), 400

    user.set_password(new_password)
    # Logging
    try:
        log_security("Password changed for user.", level=0)
    except Exception:
        pass

    return jsonify({"success": True, "message": "Password changed."})


# =============================================================================
# 4. ADMIN API ROUTES (General User Management)
# =============================================================================

@user_manager_bp.route("/admin/api/users", methods=["GET"])
@login_required
@AuthShield.require_role(["Admin"])
def get_users_api():
    """Returns a list of all users and the current user's ID (Admin only)."""
    users = User.query.order_by(User.created_at.desc()).all()

    users_data = []
    for u in users:
        created_at = u.created_at.strftime("%Y-%m-%d") if u.created_at else "N/A"
        
        users_data.append({
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "created_at": created_at,
            "is_locked": u.is_locked,
        })

    return jsonify({
        "success": True, 
        "current_user_id": current_user.id, 
        "users": users_data
    })


@user_manager_bp.route("/admin/api/users/update-email", methods=["PATCH"])
@login_required
@AuthShield.require_role(["Admin"])
@AuthShield.secure_transaction
def update_user_email():
    """Admin updates another user's email."""
    data = InputSanitizer.clean_form_data(request.get_json())
    user_id = data.get("user_id")
    new_email = data.get("email", "")

    if not user_id or not new_email:
        return jsonify({"success": False, "message": "Missing user ID or new email."}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404

    # Check conflict
    if User.query.filter(User.email == new_email).filter(User.id != user_id).first():
         return jsonify({"success": False, "message": "Email already in use by another account."}), 409

    old_email = user.email
    user.email = new_email
    
    try:
        log_security(f"Admin updated email for user {user_id}. {old_email} -> {new_email}", level=1)
    except Exception:
        pass

    return jsonify({"success": True, "message": "Email updated."})


@user_manager_bp.route("/admin/api/users/update-role", methods=["PATCH"])
@login_required
@AuthShield.require_role(["Admin"])
@AuthShield.secure_transaction
def update_user_role():
    """Admin updates another user's role."""
    data = InputSanitizer.clean_form_data(request.get_json())
    user_id = data.get("user_id")
    new_role = data.get("role", "")

    if not user_id or not new_role:
        return jsonify({"success": False, "message": "Missing user ID or new role."}), 400

    if int(user_id) == current_user.id:
        return jsonify({"success": False, "message": "You cannot change your own role."}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404

    if new_role not in ["Doctor", "Nurse", "Admin"]: 
        return jsonify({"success": False, "message": "Invalid role specified."}), 400
    
    # Restrict creating other admins if that's a policy
    
    old_role = user.role
    user.role = new_role
    
    try:
        log_security(f"Admin changed role for user {user_id}: {old_role} -> {new_role}", level=0)
    except Exception:
        pass

    return jsonify({"success": True, "message": "Role updated."})


@user_manager_bp.route("/admin/api/users/unlock", methods=["PATCH"])
@login_required
@AuthShield.require_role(["Admin"])
@AuthShield.secure_transaction
def unlock_user_api():
    """Admin unlocks a locked user account."""
    data = InputSanitizer.clean_form_data(request.get_json() or {})
    user_id = data.get("user_id")

    if not user_id:
        return jsonify({"success": False, "message": "Missing user ID."}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404

    user.unlock() # This usually commits, but our decorator handles commit too. Double commit is fine.
    
    try:
        log_security(f"Unlocked user {user.email}.", level=1)
    except Exception:
        pass
        
    return jsonify({"success": True, "message": f"User {user.name} unlocked."})


@user_manager_bp.route("/admin/api/users/reset-password/<int:user_id>", methods=["POST"])
@login_required
@AuthShield.require_role(["Admin"])
@AuthShield.secure_transaction
def reset_password_api(user_id):
    """Admin generates and sets a new random password for any user."""
    user = User.query.get_or_404(user_id)

    # Generate a strong 12-character random password
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    new_password = "".join(secrets.choice(alphabet) for i in range(12))

    user.set_password(new_password)
    
    try:
        log_security(f"Admin reset password for user {user_id}.", level=0)
    except Exception:
        pass

    return jsonify({
        "success": True,
        "message": f"New password generated and set for user ID {user_id}.",
        "new_password": new_password,
    })


@user_manager_bp.route("/admin/api/users/delete/<int:user_id>", methods=["DELETE"])
@login_required
@AuthShield.require_role(["Admin"])
@AuthShield.secure_transaction
def delete_user_api(user_id):
    """Admin deletes a user."""
    # Prevent deleting self
    if user_id == current_user.id:
        return jsonify({"success": False, "message": "You cannot delete your own account."}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404

    user_email = user.email
    user_name = user.name
    
    db.session.delete(user)
    
    try:
        log_security(f"Deleted user {user_name} ({user_email}).", level=0)
    except Exception:
        pass

    return jsonify({"success": True, "message": f"User {user_name} deleted."})


# =============================================================================
# 5. ADMIN API ROUTES (Admin Self Management)
# =============================================================================

@user_manager_bp.route("/admin/api/self/update-email", methods=["POST"])
@login_required
@AuthShield.require_role(["Admin"])
@AuthShield.secure_transaction
def update_self_email_api():
    """Admin updates their own email."""
    data = InputSanitizer.clean_form_data(request.get_json() or {})
    new_email = data.get("email", "")

    if not new_email:
        return jsonify({"success": False, "message": "Email is required."}), 400

    if "@" not in new_email:
        return jsonify({"success": False, "message": "Invalid email."}), 400

    if User.query.filter(User.email == new_email).filter(User.id != current_user.id).first():
        return jsonify({"success": False, "message": "Email already in use."}), 409

    user = User.query.get(current_user.id)
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404

    old_email = user.email
    user.email = new_email
    
    try:
        log_security(f"Admin updated own email: {old_email} -> {new_email}", level=1)
    except Exception:
        pass

    return jsonify({"success": True, "message": "Email updated."})


@user_manager_bp.route("/admin/api/self/reset-password", methods=["POST"])
@login_required
@AuthShield.require_role(["Admin"])
@AuthShield.secure_transaction
def reset_self_password_api():
    """Admin resets their own password (generates a temporary password)."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    temp_password = "".join(secrets.choice(alphabet) for i in range(12))

    user = User.query.get(current_user.id)
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404

    user.set_password(temp_password)
    
    try:
        log_security("Admin reset own password (temporary password set).", level=0)
    except Exception:
        pass

    return jsonify({
        "success": True,
        "message": "Password reset initiated. A temporary password was set.",
        "temp_password": temp_password,
    })
