import re
import logging

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from flask_login import login_required, current_user
from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError

# Adjust import according to your project structure
from app.models.patient import Patient

# New: logging helper for patient-related actions (visible to doctors & admin)
from app.utils.log_utils import log_activity

logger = logging.getLogger(__name__)

search_bp = Blueprint("search_manager", __name__, url_prefix="/api/patients")

# Recommended defaults (easy to change)
DEFAULT_LIST_LIMIT = 28
DEFAULT_SUGGEST_LIMIT = 30
MAX_LIST_LIMIT = 200
MAX_SUGGEST_LIMIT = 100

# Ensure helpful indexes exist (run once at import)
try:
    coll = Patient._get_collection()
    # Unique index on patient_id (safe if already exists)
    coll.create_index([("patient_id", 1)], unique=True, background=True)
    # Text index on name for faster prefix/case-insensitive search (text index helps full-text)
    # We will also use a regex-based prefix search which benefits from a normal index on lowercase name
    # Create a simple text index (harmless if it already exists)
    coll.create_index([("name", "text")], background=True)
except Exception as ex:
    # Important: can't use log_utils here because there's no Flask request / current_user context at import time.
    logger.warning("Could not ensure indexes on patients collection: %s", ex)


# Utility validators
_RE_ALPHA_SPACE = re.compile(r"^[A-Za-z ]+$")
_RE_DIGITS = re.compile(r"^\d+$")
_RE_SAFE_PREFIX = re.compile(
    r"^[A-Za-z][A-Za-z ]*$"
)  # name must start with a letter (for prefix searches)


@search_bp.route("/suggestions", methods=["GET"])
@login_required
def suggestions():
    """
    Suggestions endpoint for the dropdown (real-time).
    Query params:
      - q: search query (required)
      - page: int (default 1)
      - limit: int (default 30)
    Behavior:
      - If q contains letters only -> prefix search on name (case-insensitive).
      - If q contains digits only -> only accept exactly 9 digits; otherwise return empty list.
      - If q is mixed -> empty list (per your rule).
    Response:
      { items: [ {patient_id, name, ...}, ... ], page, limit, has_more }
    """
    if current_user.role == "Admin":
        return jsonify({"items": [], "page": 1, "limit": 30, "has_more": False})

    q = (request.args.get("q") or "").strip()
    
    # RBAC: Nurses can ONLY search by ID (min 9 digits).
    if current_user.role == "Nurse":
        # If query is not a valid 9-digit ID, return empty immediately.
        # This effectively hides all results unless they type a full ID.
        if not q.isdigit() or len(q) < 9:
             return jsonify({"items": [], "page": 1, "limit": 30, "has_more": False})

    page = max(1, int(request.args.get("page") or 1))
    limit = min(
        MAX_SUGGEST_LIMIT,
        max(1, int(request.args.get("limit") or DEFAULT_SUGGEST_LIMIT)),
    )
    skip = (page - 1) * limit

    if not q:
        return jsonify({"items": [], "page": page, "limit": limit, "has_more": False})

    # Mixed letters and digits -> return empty (explicit requirement)
    has_letters = any(c.isalpha() for c in q)
    has_digits = any(c.isdigit() for c in q)
    if has_letters and has_digits:
        return jsonify({"items": [], "page": page, "limit": limit, "has_more": False})

    try:
        results = []
        if has_digits:
            # digit-only query: accept exactly 9 digits according to your rule
            if not _RE_DIGITS.fullmatch(q) or len(q) != 9:
                # not a valid id; return empty results
                return jsonify(
                    {"items": [], "page": page, "limit": limit, "has_more": False}
                )
            # exact match on patient_id (fast via unique index)
            qs = Patient.objects(patient_id=q).only("patient_id", "name")
            # If you want prefix matching instead for partial ids, adjust here.
            for p in qs.skip(skip).limit(limit):
                results.append({"patient_id": p.patient_id, "name": p.name})
            has_more = len(results) == limit
            # NOTE: per your instruction, do NOT log realtime suggestions (would flood logs)
            return jsonify(
                {"items": results, "page": page, "limit": limit, "has_more": has_more}
            )

        # letters-only -> prefix name search (case-insensitive).
        # defensive: keep prefix searches short-circuited (prevent overly broad queries)
        sanitized = q.strip()
        if len(sanitized) < 1 or not _RE_ALPHA_SPACE.fullmatch(sanitized):
            return jsonify(
                {"items": [], "page": page, "limit": limit, "has_more": False}
            )

        # Use a case-insensitive anchored regex to enforce prefix search.
        # Use the raw mongo operator for better control.
        regex = f"^{re.escape(sanitized)}"
        raw = {"name": {"$regex": regex, "$options": "i"}}

        cursor = (
            Patient._get_collection()
            .find(raw, {"patient_id": 1, "name": 1})
            .sort("record_entry_date", -1)
            .skip(skip)
            .limit(limit)
        )
        for doc in cursor:
            results.append(
                {"patient_id": doc.get("patient_id"), "name": doc.get("name")}
            )

        has_more = len(results) == limit
        # NOTE: per your instruction, do NOT log realtime suggestions (would flood logs)
        return jsonify(
            {"items": results, "page": page, "limit": limit, "has_more": has_more}
        )

    except Exception as ex:
        logger.exception("Error in suggestions: %s", ex)
        return jsonify(
            {
                "items": [],
                "page": page,
                "limit": limit,
                "has_more": False,
                "error": "server_error",
            }
        ), 500
