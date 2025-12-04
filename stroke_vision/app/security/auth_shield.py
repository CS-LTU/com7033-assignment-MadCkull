from functools import wraps
from flask import abort, request, jsonify
from flask_login import current_user, logout_user
from app import db
from app.utils.log_utils import log_security, log_activity

class AuthShield:
    """
    Centralized Security System for StrokeVision.
    Handles RBAC, Session Validation, and DB Transaction Safety.
    """

    @staticmethod
    def require_role(roles):
        """
        Decorator to ensure current user has one of the allowed roles.
        :param roles: List of allowed roles (e.g. ["Admin", "Doctor"])
        """
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if not current_user.is_authenticated:
                    return abort(401)

                if current_user.role not in roles:
                    # Log unauthorized access attempt
                    try:
                        log_security(
                            f"Unauthorized access attempt to {request.path} by {current_user.email} (Role: {current_user.role}). Required: {roles}",
                            level=2
                        )
                    except Exception:
                        pass
                    
                    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
                        return jsonify({"success": False, "message": "Access denied: Insufficient privileges."}), 403
                    return abort(403)
                
                return f(*args, **kwargs)
            return decorated_function
        return decorator

    @staticmethod
    def secure_transaction(f):
        """
        Decorator for safe DB transactions. 
        Auto-commits on success, auto-rollbacks on error.
        """
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                result = f(*args, **kwargs)
                db.session.commit()
                return result
            except Exception as e:
                db.session.rollback()
                # Log critical DB failure
                try:
                    log_security(f"Transaction failed & rolled back in {f.__name__}: {str(e)}", level=3)
                except Exception:
                    pass
                
                print(f"[AuthShield] DB Transaction Error: {e}") # Server-side log
                
                if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
                    return jsonify({"success": False, "message": "A secure transaction error occurred."}), 500
                return abort(500)
        return decorated_function

    @staticmethod
    def validate_session():
        """
        Global hook to validate session integrity.
        Checks if user is locked or deleted while session is active.
        Should be registered as 'before_request'.
        """
        if current_user.is_authenticated:
            # Re-fetch user from DB to check latest status
            # Note: Flask-Login does this user loader logic, but I explicitly check specific flags here
            if hasattr(current_user, 'is_locked') and current_user.is_locked:
                try:
                    log_security(f"Terminating session for locked user: {current_user.email}", level=1)
                except Exception:
                    pass
                logout_user()
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return jsonify({"success": False, "message": "Account is locked.", "redirect": "/auth/login"}), 403
                return abort(403)

    @staticmethod
    def mask_name(name):
        """
        Masks a name string for privacy/PII protection.
        Example: 'John Doe' -> 'J*** D**'
        """
        if not name:
            return "N/A"
        parts = name.split()
        masked_parts = [p[0] + "*" * (len(p) - 1) if p else "" for p in parts]
        return " ".join(masked_parts)
