# settings.py
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app import db  # Assuming db is initialized in app

# Import your User model. Adjust the path if your structure is different.
from app.models.user import User

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/settings/view", methods=["GET"])
@login_required
def view_settings():
    """
    Renders the settings HTML fragment.
    Because we are using flask_login, 'current_user' is automatically
    available in the template, so we don't strictly need to pass it,
    but passing it explicitly can be good for clarity.
    """
    return render_template("profile/settings.html", user=current_user)


@settings_bp.route("/settings/update_profile", methods=["POST"])
@login_required
def update_profile():
    data = request.get_json()
    new_name = data.get("name")

    if not new_name:
        return jsonify({"success": False, "message": "Name cannot be empty."}), 400

    try:
        # current_user is a proxy, so we query the actual object to be safe for updates
        user = User.query.get(current_user.id)
        user.name = new_name
        db.session.commit()
        return jsonify({"success": True, "message": "Profile updated successfully."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@settings_bp.route("/settings/change_password", methods=["POST"])
@login_required
def change_password():
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

    # Use the check_password method from your User model
    if not user.check_password(current_password):
        return jsonify(
            {"success": False, "message": "Incorrect current password."}
        ), 400

    try:
        # Use the set_password method from your User model
        user.set_password(new_password)
        db.session.commit()
        return jsonify({"success": True, "message": "Password changed successfully."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
