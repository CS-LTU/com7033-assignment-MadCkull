# app/views/search_manager.py
import re
import logging
from datetime import datetime

from flask import Blueprint, request, jsonify
from flask_login import login_required
from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError

# Adjust import according to your project structure
from app.models.patient import Patient

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
    logger.warning("Could not ensure indexes on patients collection: %s", ex)


def _serialize_date(dt):
    """Return ISO formatted string for datetimes, or None."""
    if dt is None:
        return None
    if isinstance(dt, datetime):
        # Keep ISO format; leave timezone handling to database / front-end
        return dt.isoformat()
    return dt


def _patient_full_doc(p):
    """Return full patient document as JSON-serializable dict."""
    # Convert fields carefully to native types
    doc = p.to_mongo().to_dict()
    # Remove MongoDB internal _id => convert to string
    _id = doc.pop("_id", None)
    if _id is not None:
        doc["_id"] = str(_id)
    # Turn datetimes to ISO strings
    if "record_entry_date" in doc and doc["record_entry_date"] is not None:
        doc["record_entry_date"] = _serialize_date(doc["record_entry_date"])
    # ensure numeric types are safe
    if "stroke_risk" in doc and doc["stroke_risk"] is not None:
        doc["stroke_risk"] = float(doc["stroke_risk"])
    return doc


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
    q = (request.args.get("q") or "").strip()
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


@search_bp.route("/list", methods=["GET"])
@login_required
def list_patients():
    """
    Paginated patient list used by the 'Show Patient List' component.
    Query params:
      - page: int (default 1)
      - limit: int (default 28)
    Response:
      { items: [ {patient_id, name, gender, stroke_risk, record_entry_date}, ... ],
        page, limit, has_more }
    """
    page = max(1, int(request.args.get("page") or 1))
    limit = min(
        MAX_LIST_LIMIT, max(1, int(request.args.get("limit") or DEFAULT_LIST_LIMIT))
    )
    skip = (page - 1) * limit

    try:
        items = []
        # projection to fetch only required fields (faster)
        cursor = (
            Patient._get_collection()
            .find(
                {},
                {
                    "patient_id": 1,
                    "name": 1,
                    "gender": 1,
                    "stroke_risk": 1,
                    "record_entry_date": 1,
                },
            )
            .sort("record_entry_date", -1)
            .skip(skip)
            .limit(limit)
        )

        for doc in cursor:
            items.append(
                {
                    "patient_id": doc.get("patient_id"),
                    "name": doc.get("name"),
                    "gender": doc.get("gender"),
                    "stroke_risk": float(doc.get("stroke_risk") or 0),
                    "record_entry_date": _serialize_date(doc.get("record_entry_date")),
                }
            )

        has_more = len(items) == limit
        return jsonify(
            {"items": items, "page": page, "limit": limit, "has_more": has_more}
        )

    except Exception as ex:
        logger.exception("Error listing patients: %s", ex)
        return jsonify(
            {
                "items": [],
                "page": page,
                "limit": limit,
                "has_more": False,
                "error": "server_error",
            }
        ), 500


@search_bp.route("/<string:patient_id>", methods=["GET"])
@login_required
def get_patient(patient_id):
    """
    Full patient detail endpoint. patient_id must be 9 digits.
    """
    if not _RE_DIGITS.fullmatch(patient_id) or len(patient_id) != 9:
        return jsonify(
            {
                "error": "invalid_patient_id",
                "message": "patient_id must be exactly 9 digits",
            }
        ), 400

    try:
        p = Patient.objects.get(patient_id=patient_id)
        return jsonify(_patient_full_doc(p))
    except DoesNotExist:
        return jsonify({"error": "not_found"}), 404
    except MongoValidationError as mv:
        logger.exception("Validation error fetching patient %s: %s", patient_id, mv)
        return jsonify({"error": "invalid_request"}), 400
    except Exception as ex:
        logger.exception("Error fetching patient %s: %s", patient_id, ex)
        return jsonify({"error": "server_error"}), 500


# NOTE:
# - Register this blueprint inside your create_app() function:
#     from app.views.search_manager import search_bp
#     app.register_blueprint(search_bp)   # default prefix: /api/patients
#
# - If you want a different prefix, change url_prefix in Blueprint(...) above
#
# - Consider enabling text indexes or a dedicated lowercase-name index for faster prefix searches.
#   Mongo text index is created above as a recommendation; you can also create an index on a 'name_lower' field
#   if you want very fast prefix searches at scale (store lowercase(name) on write).
#
# - For infinite-scroll: frontend should call /api/patients/suggestions?q=...&page=1..N&limit=30 (or list with limit=28)
#
