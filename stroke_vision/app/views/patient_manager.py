# views/patient_manager.py
from flask import Blueprint, abort, render_template, url_for, request, jsonify, flash, redirect
from app.forms.patient_form import PatientForm
from app.models.patient import Patient
from app.utils.prediction import StrokePredictor
from app.utils.id_generator import IDGenerator
from app.utils.log_utils import log_activity
from datetime import datetime
from flask_login import current_user, login_required
import traceback
import numpy as np
import json

# Security
from app.security.auth_shield import AuthShield
from app.security.input_sanitizer import InputSanitizer, ValidationError

patient_bp = Blueprint("patient", __name__)
stroke_predictor = StrokePredictor()

# =======================================================
# UTILITIES AND HELPERS
# =======================================================

def is_ajax_request():
    """Checks if the request is an AJAX request."""
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"

def map_binary_to_yes_no(value):
    return "Yes" if value == "1" else "No"

def map_smoking_status(status):
    mapping = {
        "formerly smoked": "Formerly Smoked",
        "never smoked": "Never Smoked",
        "smokes": "Smokes",
        "Unknown": "Unknown",
    }
    return mapping.get(status, status)

def map_work_type(work):
    mapping = {
        "Private": "Private",
        "Self-employed": "Self-Employed",
        "Govt_job": "Govt Job",
        "children": "Children",
        "Never_worked": "Never Worked",
    }
    return mapping.get(work, work)

def map_residence_type(residence):
    return "Urban" if residence == "Urban" else "Rural"

def map_gender(gender):
    return "Other" if gender == "Other" else gender

def get_risk_level(risk_percentage):
    if risk_percentage < 20: return "Low"
    elif risk_percentage < 40: return "Moderate"
    elif risk_percentage < 60: return "High"
    elif risk_percentage < 80: return "Very High"
    else: return "Critical"

def get_risk_class(risk_level):
    if risk_level in ["Critical", "Very High"]: return "risk-critical"
    elif risk_level == "High": return "risk-high"
    elif risk_level == "Moderate": return "risk-moderate"
    else: return "risk-low"

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.int_, np.intc, np.intp, np.int8, np.int16, np.int32, np.int64, np.uint8, np.uint16, np.uint32, np.uint64)):
            return int(obj)
        elif isinstance(obj, (np.float_, np.float16, np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

# =======================================================
# DATA API ENDPOINT (For client-side data fetching)
# =======================================================

@patient_bp.route("/api/data", methods=["GET"])
@login_required
@AuthShield.require_role(["Doctor"])
def api_patient_data():
    """Fetches paginated patient data as JSON."""
    if not is_ajax_request():
        return jsonify({"error": "Unauthorized access to data API"}), 403

    try:
        page = request.args.get("page", 1, type=int)
        limit = 20
        skip = (page - 1) * limit
        patients = Patient.objects.order_by("-record_entry_date").skip(skip).limit(limit)
        total_count = Patient.objects.count()

        log_activity(f"Accessed patient list via API (page={page}, limit={limit}).", level=1)
        
        import time
        time.sleep(1.2)  # Artificial delay

        patient_list = []
        for patient in patients:
            patient_list.append({
                "id": str(patient.id),
                "patient_id": patient.patient_id,
                "name": patient.name,
                "age": patient.age,
                "gender": patient.gender,
                "risk_level": get_risk_level(patient.stroke_risk),
                "added_on": patient.record_entry_date.strftime("%Y-%m-%d"),
                "stroke_risk": patient.stroke_risk,
            })

        return jsonify({
            "patients": patient_list,
            "page": page,
            "limit": limit,
            "has_next": (page * limit) < total_count,
            "total_count": total_count,
        })
    except Exception as e:
        log_activity(f"Error fetching patient data: {str(e)}", level=3)
        return jsonify({"success": False, "message": "Failed to load patient data."}), 500

# --- View Routes ---

@patient_bp.route("/views/list", methods=["GET"])
@login_required
@AuthShield.require_role(["Doctor"])
def api_patient_list_view():
    """Renders the HTML container for the Patient List view."""
    return render_template("patient/patient_list_fragment.html")


@patient_bp.route("/views/details/<patient_id>", methods=["GET"])
@login_required
@AuthShield.require_role(["Doctor", "Nurse"])
def api_details_patient_view(patient_id):
    """Fetches patient data and renders the HTML fragment for the details view."""
    # Validate patient ID format
    try:
        InputSanitizer.validate_patient_id(patient_id)
    except ValidationError as e:
        return jsonify({"success": False, "message": str(e)}), 400

    patient = Patient.objects(patient_id=patient_id).first()

    if not patient:
        log_activity(f"Patient details requested but not found: {patient_id}", level=2)
        return jsonify({"error": "Patient not found"}), 404

    log_activity(f"Viewed patient {patient_id}", level=1)

    risk_level_str = patient.risk_level if hasattr(patient, "risk_level") else "Low"
    risk_class_str = get_risk_class(risk_level_str)

    patient_data = {
        "patient_id": patient.patient_id,
        "name": patient.name,
        "age": patient.age,
        "gender": patient.gender,
        "ever_married": patient.ever_married,
        "work_type": patient.work_type,
        "residence_type": patient.residence_type,
        "heart_disease": patient.heart_disease,
        "hypertension": patient.hypertension,
        "avg_glucose_level": patient.avg_glucose_level,
        "bmi": patient.bmi,
        "smoking_status": patient.smoking_status,
        "stroke_risk": patient.stroke_risk,
        "risk_level": risk_level_str,
        "risk_class": risk_class_str,
        "record_entry_date": patient.record_entry_date.strftime("%b %d, %Y") if patient.record_entry_date else "N/A",
        "created_by": patient.created_by,
    }

    return render_template("patient/patient_details_fragment.html", patient=patient_data)


# --------------------Add/Edit Patients route----------------------
@patient_bp.route("/form", defaults={"patient_id": None}, methods=["GET", "POST"])
@patient_bp.route("/form/<patient_id>", methods=["GET", "POST"])
@login_required
@AuthShield.require_role(["Doctor", "Nurse"])
@AuthShield.secure_transaction # Catches unexpected errors
def patient_form(patient_id):
    """Handles both adding a new patient and editing an existing one."""
    patient = None

    # Handle GET Request
    if request.method == "GET":
        if patient_id:
            try:
                patient = Patient.objects(patient_id=patient_id).first()
                if not patient:
                    flash(f"Patient ID {patient_id} not found.", "warning")
                    return redirect(url_for("home"))

                form = PatientForm(obj=patient)
                if is_ajax_request():
                    return render_template("patient/patient_form_fragment.html", form=form, patient=patient, mode="edit")
                else:
                    return render_template("patient/edit_patient.html", form=form, patient=patient)
            except Exception as e:
                log_activity(f"Error loading patient {patient_id} for edit: {str(e)}", level=3)
                flash("Error loading patient details for editing.", "danger")
                return redirect(url_for("home"))
        else:
            form = PatientForm()
            if is_ajax_request():
                return render_template("patient/patient_form_fragment.html", form=form, patient=None, mode="add")
            else:
                return render_template("patient/add_patient.html", form=form)

    # Handle POST
    elif request.method == "POST":
        form = PatientForm()
        if not form.validate_on_submit():
            # Return first validation error
            for field, errors in form.errors.items():
                return jsonify({"success": False, "message": errors[0]}), 400

        # Validate patient data with strict rules before processing
        try:
            InputSanitizer.validate_patient_data(form.data)
        except ValidationError as e:
            return jsonify({"success": False, "message": str(e)}), 400

        # Sanitize text fields (I'll use this later in case I need it, currently sanitization is already being done by the form)
        clean_data = InputSanitizer.clean_form_data(form.data)

        patient_id_from_form = request.form.get("patient_id")
        is_edit = bool(patient_id_from_form)

        # Prepare features for prediction (using clean string values or form values)
        input_features = {
            k: v for k, v in form.data.items() if k not in ["csrf_token", "submit", "patient_id"]
        }
        
        # Recalculate risk
        risk_percent, risk_level = stroke_predictor.predict_risk(input_features)

        if is_edit:
            patient = Patient.objects(patient_id=patient_id_from_form).first()
            if not patient:
                return jsonify({"success": False, "message": "Patient not found for update"}), 404
        else:
            patient = Patient()
            patient.patient_id = IDGenerator.generate_id()
            patient.record_entry_date = datetime.now()
            patient.created_by = current_user.name

        # Mapping and Setting
        patient.name = InputSanitizer.sanitize_text(form.name.data) # Sanitize Name strictly
        patient.gender = map_gender(form.gender.data)
        patient.age = form.age.data
        patient.hypertension = int(form.hypertension.data)
        patient.heart_disease = int(form.heart_disease.data)
        patient.ever_married = form.ever_married.data
        patient.work_type = map_work_type(form.work_type.data)
        patient.residence_type = map_residence_type(form.residence_type.data)
        patient.avg_glucose_level = form.avg_glucose_level.data
        patient.bmi = form.bmi.data
        patient.smoking_status = map_smoking_status(form.smoking_status.data)
        
        patient.stroke_risk = risk_percent
        patient.risk_level = risk_level

        patient.save()

        action_log = f"Updated patient {patient.patient_id}" if is_edit else f"Added patient {patient.patient_id}"
        log_activity(f"{action_log} (Risk: {risk_level})", level=1)

        return jsonify({
            "success": True, 
            "message": f"Patient record {'updated' if is_edit else 'added'}.",
            "patient_id": patient.patient_id,
            "risk": risk_percent,
            "risk_level": risk_level,
            "redirect": url_for("home")
        })


@patient_bp.route("/predict", methods=["POST"])
@login_required
@AuthShield.require_role(["Doctor", "Nurse"])
@AuthShield.secure_transaction
def predict_risk():
    """Predicts risk and optionally saves/updates patient."""
    # Sanitize form data (skips password fields automatically)
    raw_data = InputSanitizer.clean_form_data(request.form)
    
    # Validate all patient data with strict rules
    try:
        InputSanitizer.validate_patient_data(raw_data)
    except ValidationError as e:
        log_activity(f"Validation failed: {str(e)}", level=2)
        return jsonify({"success": False, "message": str(e)}), 400
    
    # Extract prediction fields
    try:
        prediction_data = {
            "age": raw_data.get("age"),
            "gender": raw_data.get("gender"),
            "hypertension": raw_data.get("hypertension"),
            "heart_disease": raw_data.get("heart_disease"),
            "ever_married": raw_data.get("ever_married"),
            "work_type": raw_data.get("work_type"),
            "residence_type": raw_data.get("residence_type"),
            "avg_glucose_level": raw_data.get("avg_glucose_level"),
            "bmi": raw_data.get("bmi"),
            "smoking_status": raw_data.get("smoking_status"),
        }
        
        risk_percentage = float(stroke_predictor.predict_risk(prediction_data))
        risk_level = get_risk_level(risk_percentage)
        
        log_activity(f"Prediction computed: risk={risk_percentage}", level=1)
        
    except ValueError as e:
        log_activity(f"Prediction failed due to bad input: {str(e)}", level=2)
        return jsonify({"success": False, "message": str(e)}), 400

    # Save logic if applicable
    patient_id = raw_data.get("patient_id")
    
    # Determine Patient Object
    patient = None
    if patient_id:
        patient = Patient.objects(patient_id=patient_id).first()
    
    # If creating new
    if not patient:
        patient = Patient()
        patient.patient_id = IDGenerator.generate_patient_id()
        patient.record_entry_date = datetime.now()
        patient.created_by = current_user.name
        is_new = True
    else:
        is_new = False
    
    patient.name = raw_data.get("name", patient.name)
    if raw_data.get("age"): patient.age = int(raw_data.get("age"))
    patient.gender = raw_data.get("gender") or patient.gender
    patient.ever_married = raw_data.get("ever_married") or patient.ever_married
    patient.work_type = map_work_type(raw_data.get("work_type")) or patient.work_type
    patient.residence_type = raw_data.get("residence_type") or patient.residence_type
    patient.heart_disease = map_binary_to_yes_no(raw_data.get("heart_disease"))
    patient.hypertension = map_binary_to_yes_no(raw_data.get("hypertension"))
    
    if raw_data.get("avg_glucose_level"): patient.avg_glucose_level = float(raw_data.get("avg_glucose_level"))
    if raw_data.get("bmi"): patient.bmi = float(raw_data.get("bmi"))
    patient.smoking_status = map_smoking_status(raw_data.get("smoking_status")) or patient.smoking_status
    
    patient.stroke_risk = risk_percentage
    patient.risk_level = risk_level
    
    try:
        if not is_new:
            patient.updated_by = current_user.name
            patient.updated_at = datetime.now()
    except: pass

    patient.save()

    log_activity(f"{'Created' if is_new else 'Updated'} patient {patient.patient_id} via Predict API", level=1)

    return json.dumps({
        "success": True,
        "patient_id": patient.patient_id,
        "name": patient.name,
        "risk": risk_percentage,
        "risk_level": risk_level,
        "message": "Patient data saved."
    }, cls=NumpyEncoder), 200, {"Content-Type": "application/json"}


@patient_bp.route("/api/delete/<patient_id>", methods=["DELETE"])
@login_required
@AuthShield.require_role(["Doctor"])
@AuthShield.secure_transaction
def delete_patient(patient_id):
    # Validate patient ID format before DB query
    try:
        InputSanitizer.validate_patient_id(patient_id)
    except ValidationError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    
    patient = Patient.objects(patient_id=patient_id).first()
    if not patient:
        return jsonify({"success": False, "message": "Patient not found"}), 404

    patient.delete()
    log_activity(f"Deleted patient record: {patient_id}", level=1)

    return jsonify({"success": True, "message": "Patient record deleted.", "redirect": url_for("home")})


@patient_bp.route("/count", methods=["GET"])
@login_required
def patients_count():
    try:
        count = Patient.objects.count()
        return jsonify({"count": count})
    except Exception as error:
        log_activity(f"Error counting patients: {str(error)}", level=3)
        return jsonify({"error": "Failed to count patients"}), 500
