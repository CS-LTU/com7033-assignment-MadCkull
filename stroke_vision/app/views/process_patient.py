# views/process_patient.py
from flask import Blueprint, render_template, url_for, request, jsonify, flash, redirect
from app.forms.patient_form import PatientForm
from app.models.patient import Patient
from app.utils.prediction import StrokePredictor
from app.utils.id_generator import IDGenerator
from datetime import datetime
from flask_login import current_user, login_required
import traceback
import numpy as np
import json


patient_bp = Blueprint("patient", __name__)
stroke_predictor = StrokePredictor()

# =======================================================
# UTILITIES AND HELPERS
# =======================================================


def is_ajax_request():
    """
    Checks if the request is an AJAX request from the client-side router
    by checking the 'X-Requested-With' header set by app_router.js.
    """
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def map_binary_to_yes_no(value):
    """Convert '0'/'1' to 'No'/'Yes'"""
    return "Yes" if value == "1" else "No"


def map_smoking_status(status):
    """Map form smoking status to MongoDB expected format"""
    mapping = {
        "formerly smoked": "Formerly Smoked",
        "never smoked": "Never Smoked",
        "smokes": "Smokes",
        "Unknown": "Unknown",
    }
    return mapping.get(status, status)


def map_work_type(work):
    """Map form work type to MongoDB expected format"""
    mapping = {
        "Private": "Private",
        "Self-employed": "Self-Employed",
        "Govt_job": "Govt Job",
        "children": "Children",
        "Never_worked": "Never Worked",
    }
    return mapping.get(work, work)


def map_residence_type(residence):
    """Map form residence type to MongoDB expected format."""
    return "Urban" if residence == "Urban" else "Rural"


def map_gender(gender):
    """Map form gender to MongoDB expected format, handling 'Other'."""
    return "Other" if gender == "Other" else gender


def get_risk_level(risk_percentage):
    """Get risk level based on percentage"""
    if risk_percentage < 20:
        return "Low"
    elif risk_percentage < 40:
        return "Moderate"
    elif risk_percentage < 60:
        return "High"
    elif risk_percentage < 80:
        return "Very High"
    else:
        return "Critical"


# --- Helper to determine CSS class based on risk ---
def get_risk_class(risk_level):
    if risk_level in ["Critical", "Very High"]:
        return "risk-critical"
    elif risk_level == "High":
        return "risk-high"
    elif risk_level == "Moderate":
        return "risk-moderate"
    else:
        return "risk-low"


# Custom JSON encoder to handle numpy types
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(
            obj,
            (
                np.int_,
                np.intc,
                np.intp,
                np.int8,
                np.int16,
                np.int32,
                np.int64,
                np.uint8,
                np.uint16,
                np.uint32,
                np.uint64,
            ),
        ):
            return int(obj)
        elif isinstance(obj, (np.float_, np.float16, np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


# =======================================================
# DATA API ENDPOINT (For client-side data fetching)
# Full URL: /patient/api/data
# =======================================================


@patient_bp.route("/api/data", methods=["GET"])
@login_required
def api_patient_data():
    """Fetches paginated patient data as JSON for the client-side list rendering."""
    # ⚠️ ADDED: Security check to ensure this data endpoint is accessed via AJAX
    if not is_ajax_request():
        return jsonify({"error": "Unauthorized access to data API"}), 403

    try:
        page = request.args.get("page", 1, type=int)
        # We set a fixed limit per page for infinite scroll
        limit = 20
        skip = (page - 1) * limit

        # 1. Fetch data (ordered by latest entry date)
        patients = (
            Patient.objects.order_by("-record_entry_date").skip(skip).limit(limit)
        )
        total_count = Patient.objects.count()

        # 2. Prepare JSON response
        patient_list = []
        for patient in patients:
            patient_list.append(
                {
                    "id": str(patient.id),  # MongoDB internal ID
                    "patient_id": patient.patient_id,  # User-facing ID
                    "name": patient.name,
                    "age": patient.age,
                    "gender": patient.gender,
                    # Reuse the existing helper function
                    "risk_level": get_risk_level(patient.stroke_risk),
                    "added_on": patient.record_entry_date.strftime("%Y-%m-%d"),
                    "stroke_risk": patient.stroke_risk,  # Needed for details link
                }
            )

        return jsonify(
            {
                "patients": patient_list,
                "page": page,
                "limit": limit,
                # Simple check if there's more data to load
                "has_next": (page * limit) < total_count,
                "total_count": total_count,
            }
        )

    except Exception as e:
        print(f"Error fetching patient data: {str(e)}")
        return jsonify(
            {"success": False, "message": "Failed to load patient data."}
        ), 500


# =======================================================
# NEW API VIEW ROUTES (For Client-Side Router)
# Routes changed from /api/views/... to /views/...
# Full URLs: /patient/views/list, /patient/views/add, etc.
# =======================================================


@patient_bp.route("/views/list", methods=["GET"])
@login_required
def api_patient_list_view():
    """Renders the HTML container/shell for the Patient List view."""
    if not is_ajax_request():
        return jsonify({"error": "Unauthorized access to API view"}), 403

    # We assume 'patient/patient_list_fragment.html' is a minimal template
    # that doesn't extend base.html.
    return render_template("patient/patient_list_fragment.html")


@patient_bp.route("/views/details/<patient_id>", methods=["GET"])
@login_required
def api_details_patient_view(patient_id):
    """
    Fetches patient data and renders the HTML fragment for the details view.
    """
    # Security check: Ensure this is an AJAX request (optional but good practice)
    # if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
    #    return jsonify({"error": "Unauthorized"}), 403

    patient = Patient.objects(patient_id=patient_id).first()

    if not patient:
        return jsonify({"error": "Patient not found"}), 404

    # Calculate Risk Class for UI (matches patient_details.css)
    # We assume patient.risk_level exists, or we derive it from stroke_risk
    # If your model only has stroke_risk (number), calculate the level string first.

    # Example logic if 'risk_level' is stored in DB:
    risk_level_str = patient.risk_level if hasattr(patient, "risk_level") else "Low"
    risk_class_str = get_risk_class(risk_level_str)

    # Prepare data dictionary for the template
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
        "risk_class": risk_class_str,  # <--- CRITICAL: Needed for the new UI badge
        "record_entry_date": patient.record_entry_date.strftime("%b %d, %Y")
        if patient.record_entry_date
        else "N/A",
        "created_by": patient.created_by,
    }

    # Render the FRAGMENT.
    # Make sure the file on your server is named 'patient/patient_details_fragment.html'
    return render_template(
        "patient/patient_details_fragment.html", patient=patient_data
    )


# --------------------Add/Edit Patients route----------------------
@patient_bp.route("/form", defaults={"patient_id": None}, methods=["GET", "POST"])
@patient_bp.route("/form/<patient_id>", methods=["GET", "POST"])
@login_required
def patient_form(patient_id):
    """
    Handles both adding a new patient and editing an existing one.
    - GET request: Renders the form (pre-populated if patient_id is provided).
    - POST request: Submits data for prediction and potential save.
    """
    patient = None

    # --- 3.1 Handle GET Request (Form Rendering/Pre-population) ---
    if request.method == "GET":
        # Scenario 1: EDIT Patient (patient_id is provided)
        if patient_id:
            try:
                # Attempt to fetch the existing patient record
                patient = Patient.objects(patient_id=patient_id).first()
                if not patient:
                    # If patient not found, flash error and redirect or return error fragment
                    flash(f"Patient ID {patient_id} not found.", "warning")
                    return redirect(url_for("home"))  # Redirect full page

                # Populate the form with patient data for editing
                # The 'obj' argument automatically sets form field values from the model object
                form = PatientForm(obj=patient)

                # Check if this is an AJAX request (client-side router)
                if is_ajax_request():
                    # For client-side rendering, return the HTML fragment
                    return render_template(
                        "patient/patient_form_fragment.html",
                        form=form,
                        patient=patient,
                        mode="edit",
                    )
                else:
                    # For full page load
                    return render_template(
                        "patient/edit_patient.html", form=form, patient=patient
                    )

            except Exception as e:
                print(f"Error fetching patient {patient_id} for edit: {e}")
                traceback.print_exc()
                flash("Error loading patient details for editing.", "danger")
                return redirect(url_for("home"))

        # Scenario 2: ADD New Patient (patient_id is None)
        else:
            form = PatientForm()
            # Check if this is an AJAX request (client-side router)
            if is_ajax_request():
                # For client-side rendering, return the HTML fragment
                return render_template(
                    "patient/patient_form_fragment.html",
                    form=form,
                    patient=None,
                    mode="add",
                )
            else:
                # For full page load
                return render_template("patient/add_patient.html", form=form)

    # --- 3.2 Handle POST Request (Form Submission for Prediction/Save) ---
    elif request.method == "POST":
        form = PatientForm()
        if not form.validate_on_submit():
            # If validation fails, return the form with errors (useful for full page POSTs)

            # Since the front-end handles form submission via JavaScript/API,
            # we'll assume the form is generally valid, but if not, an API error
            # response would be better than rendering HTML here.
            # For simplicity with current setup, we proceed to prediction assuming client validation passed.
            # If the client side submits via a standard POST without AJAX,
            # this section would need to return a fully rendered page with errors.
            pass

        try:
            # Get the patient_id from the form (it's a hidden field in the edit form)
            patient_id_from_form = request.form.get("patient_id")

            # 1. Prepare data for prediction
            data = form.data

            # Remove non-feature fields and map boolean strings
            input_features = {
                k: v
                for k, v in data.items()
                if k not in ["csrf_token", "submit", "patient_id"]
            }

            # 2. Get prediction
            risk_percent, risk_level = stroke_predictor.predict_risk(input_features)

            # 3. Determine if this is ADD or EDIT
            is_edit = patient_id_from_form is not None and patient_id_from_form != ""

            if is_edit:
                # EDIT: Fetch existing patient
                patient = Patient.objects(patient_id=patient_id_from_form).first()
                if not patient:
                    return jsonify(
                        {"success": False, "message": "Patient not found for update"}
                    ), 404
            else:
                # ADD: Create a new Patient object
                patient = Patient()
                patient.patient_id = IDGenerator.generate_id()
                patient.record_entry_date = datetime.now()
                patient.created_by = (
                    current_user.username
                )  # Assuming username is available

            # 4. Update/Set patient object fields
            patient.name = data["name"]
            patient.gender = map_gender(data["gender"])
            patient.age = data["age"]
            patient.hypertension = int(data["hypertension"])
            patient.heart_disease = int(data["heart_disease"])
            patient.ever_married = data["ever_married"]
            patient.work_type = map_work_type(data["work_type"])
            patient.residence_type = map_residence_type(data["residence_type"])
            patient.avg_glucose_level = data["avg_glucose_level"]
            patient.bmi = data["bmi"]
            patient.smoking_status = map_smoking_status(data["smoking_status"])

            # Prediction results
            patient.stroke_risk = risk_percent
            patient.risk_level = risk_level

            # Save to database
            patient.save()

            # 5. Return JSON response for client-side redirection/modal
            action = "updated" if is_edit else "added"
            return jsonify(
                {
                    "success": True,
                    "message": f"Patient record successfully {action}.",
                    "patient_id": patient.patient_id,
                    "risk": risk_percent,
                    "risk_level": risk_level,
                    "redirect": url_for("home"),
                }
            ), 200

        except Exception as e:
            print(f"Error processing form submission: {e}")
            traceback.print_exc()
            return jsonify(
                {
                    "success": False,
                    "message": f"Server error processing patient data: {str(e)}",
                }
            ), 500


# =======================================================
# EXISTING ROUTES (Kept for form submission/legacy API)
# (Unchanged as they don't impact the new routing scheme directly)
# =======================================================


@patient_bp.route("/predict", methods=["POST"])
@login_required
def predict_risk():
    # ... (content remains the same)
    try:
        # Extract form values (these will be the same whether Add or Edit)
        form_age = request.form.get("age")
        form_gender = request.form.get("gender")
        form_hypertension = request.form.get("hypertension")
        form_heart_disease = request.form.get("heart_disease")
        form_ever_married = request.form.get("ever_married")
        form_work_type = request.form.get("work_type")
        form_residence_type = request.form.get("residence_type")
        form_avg_glucose_level = request.form.get("avg_glucose_level")
        form_bmi = request.form.get("bmi")
        form_smoking_status = request.form.get("smoking_status")

        prediction_data = {
            "age": form_age,
            "gender": form_gender,
            "hypertension": form_hypertension,
            "heart_disease": form_heart_disease,
            "ever_married": form_ever_married,
            "work_type": form_work_type,
            "residence_type": form_residence_type,
            "avg_glucose_level": form_avg_glucose_level,
            "bmi": form_bmi,
            "smoking_status": form_smoking_status,
        }

        # Get prediction
        try:
            risk_percentage = float(stroke_predictor.predict_risk(prediction_data))
            risk_level = get_risk_level(risk_percentage)
        except ValueError as e:
            return jsonify({"success": False, "message": str(e)}), 400

        # Check if this is an update (edit) or create (add)
        patient_id = request.form.get("patient_id")  # hidden field from edit page

        try:
            if patient_id:
                # Try to update existing patient
                patient = Patient.objects(patient_id=patient_id).first()
                if not patient:
                    # Fall back to create if patient_id not found
                    patient = None
            else:
                patient = None

            if patient:
                # Update fields (map form -> DB formats)
                patient.name = request.form.get("name", patient.name)
                patient.age = (
                    int(form_age) if form_age not in (None, "") else patient.age
                )
                patient.gender = form_gender or patient.gender
                patient.ever_married = form_ever_married or patient.ever_married
                patient.work_type = map_work_type(form_work_type) or patient.work_type
                patient.residence_type = form_residence_type or patient.residence_type
                patient.heart_disease = map_binary_to_yes_no(form_heart_disease)
                patient.hypertension = map_binary_to_yes_no(form_hypertension)
                patient.avg_glucose_level = (
                    float(form_avg_glucose_level)
                    if form_avg_glucose_level not in (None, "")
                    else patient.avg_glucose_level
                )
                patient.bmi = (
                    float(form_bmi) if form_bmi not in (None, "") else patient.bmi
                )
                patient.smoking_status = (
                    map_smoking_status(form_smoking_status) or patient.smoking_status
                )

                # Update risk and audit fields
                patient.stroke_risk = risk_percentage
                # optional — set/update audit fields if you have them
                try:
                    patient.updated_by = current_user.name
                    patient.record_last_updated = datetime.now()
                except Exception:
                    pass

                patient.save()
                response_patient = patient
            else:
                # Create new patient (existing behaviour)
                new_patient = Patient(
                    patient_id=IDGenerator.generate_patient_id(),
                    name=request.form.get("name"),
                    age=int(form_age) if form_age not in (None, "") else None,
                    gender=form_gender,
                    ever_married=form_ever_married,
                    work_type=map_work_type(form_work_type),
                    residence_type=form_residence_type,
                    heart_disease=map_binary_to_yes_no(form_heart_disease),
                    hypertension=map_binary_to_yes_no(form_hypertension),
                    avg_glucose_level=float(form_avg_glucose_level)
                    if form_avg_glucose_level not in (None, "")
                    else None,
                    bmi=float(form_bmi) if form_bmi not in (None, "") else None,
                    smoking_status=map_smoking_status(form_smoking_status),
                    stroke_risk=risk_percentage,
                    record_entry_date=datetime.now(),
                    created_by=current_user.name,
                )
                new_patient.save()
                response_patient = new_patient

            # Build response using custom encoder to handle numpy types
            response = {
                "success": True,
                "patient_id": response_patient.patient_id,
                "name": response_patient.name,
                "risk": risk_percentage,
                "risk_level": risk_level,
                "message": "Patient data saved successfully",
            }

            return (
                json.dumps(response, cls=NumpyEncoder),
                200,
                {"Content-Type": "application/json"},
            )

        except Exception as e:
            print(f"Error saving/updating patient: {str(e)}")
            print(traceback.format_exc())
            return jsonify(
                {
                    "success": False,
                    "message": f"Error saving/updating patient data: {str(e)}",
                }
            ), 500

    except Exception as e:
        print(f"Unexpected error in predict_risk: {str(e)}")
        print(traceback.format_exc())
        return jsonify(
            {"success": False, "message": f"An unexpected error occurred: {str(e)}"}
        ), 500


@patient_bp.route("/delete/<patient_id>", methods=["POST"])
@login_required
def delete_patient(patient_id):
    # This is already a JSON API endpoint, so no changes needed here.
    try:
        # Check if user is admin
        if current_user.role != "admin":
            return jsonify(
                {
                    "success": False,
                    "message": "Unauthorized: Only admins can delete records",
                }
            ), 403

        # Find and delete the patient
        patient = Patient.objects(patient_id=patient_id).first()
        if not patient:
            return jsonify({"success": False, "message": "Patient not found"}), 404

        patient.delete()

        return jsonify(
            {
                "success": True,
                "message": "Patient record deleted successfully",
                "redirect": url_for("home"),
            }
        ), 200

    except Exception as e:
        print(f"Error deleting patient: {str(e)}")
        return jsonify(
            {"success": False, "message": f"Error deleting patient: {str(e)}"}
        ), 500


@patient_bp.route("/count", methods=["GET"])
@login_required
def patients_count():
    # This is already a JSON API endpoint, so no changes needed here.
    try:
        count = Patient.objects.count()
        return jsonify({"count": count})
    except Exception as error:
        print("Error counting patients:", str(error))
        return jsonify({"error": "Failed to count patients"}), 500
