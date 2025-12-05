# views/patient_manager.py
from flask import Blueprint, render_template, url_for, request, jsonify, flash, redirect
from app.forms.patient_form import PatientForm
from app.models.patient import Patient
from app.utils.prediction import StrokePredictor
from app.utils.id_generator import IDGenerator
from app.utils.log_utils import log_security, log_activity
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


def get_risk_class(risk_level):
    if risk_level in ["Critical", "Very High"]:
        return "risk-critical"
    elif risk_level == "High":
        return "risk-high"
    elif risk_level == "Moderate":
        return "risk-moderate"
    else:
        return "risk-low"


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
# =======================================================


@patient_bp.route("/api/data", methods=["GET"])
@login_required
def api_patient_data():
    """Fetches paginated patient data as JSON."""
    # Security check
    if not is_ajax_request():
        log_security("Unauthorized API data access attempt.", level=3)
        return jsonify({"error": "Unauthorized access to data API"}), 403

    try:
        page = request.args.get("page", 1, type=int)
        limit = 20
        skip = (page - 1) * limit

        patients = (
            Patient.objects.order_by("-record_entry_date").skip(skip).limit(limit)
        )
        total_count = Patient.objects.count()

        log_activity(
            f"Accessed patient list via API (page={page}, limit={limit}).", level=1
        )

        patient_list = []
        for patient in patients:
            patient_list.append(
                {
                    "id": str(patient.id),
                    "patient_id": patient.patient_id,
                    "name": patient.name,
                    "age": patient.age,
                    "gender": patient.gender,
                    "risk_level": get_risk_level(patient.stroke_risk),
                    "added_on": patient.record_entry_date.strftime("%Y-%m-%d"),
                    "stroke_risk": patient.stroke_risk,
                }
            )

        return jsonify(
            {
                "patients": patient_list,
                "page": page,
                "limit": limit,
                "has_next": (page * limit) < total_count,
                "total_count": total_count,
            }
        )

    except Exception as e:
        print(f"Error fetching patient data: {str(e)}")
        log_activity(f"Error fetching patient data: {str(e)}", level=3)
        return jsonify(
            {"success": False, "message": "Failed to load patient data."}
        ), 500


# --- View Routes ---


@patient_bp.route("/views/list", methods=["GET"])
@login_required
def api_patient_list_view():
    """Renders the HTML container for the Patient List view."""
    if not is_ajax_request():
        log_security("Unauthorized access to patient list view endpoint.", level=3)
        return jsonify({"error": "Unauthorized access to API view"}), 403

    return render_template("patient/patient_list_fragment.html")


@patient_bp.route("/views/details/<patient_id>", methods=["GET"])
@login_required
def api_details_patient_view(patient_id):
    """
    Fetches patient data and renders the HTML fragment for the details view.
    """
    patient = Patient.objects(patient_id=patient_id).first()

    if not patient:
        log_activity(f"Patient details requested but not found: {patient_id}", level=2)
        return jsonify({"error": "Patient not found"}), 404

    log_activity(f"Viewed patient details: {patient_id}", level=1)

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
        "record_entry_date": patient.record_entry_date.strftime("%b %d, %Y")
        if patient.record_entry_date
        else "N/A",
        "created_by": patient.created_by,
    }

    return render_template(
        "patient/patient_details_fragment.html", patient=patient_data
    )


# --------------------Add/Edit Patients route----------------------
@patient_bp.route("/form", defaults={"patient_id": None}, methods=["GET", "POST"])
@patient_bp.route("/form/<patient_id>", methods=["GET", "POST"])
@login_required
def patient_form(patient_id):
    """Handles both adding a new patient and editing an existing one."""
    patient = None

    # Handle GET Request
    if request.method == "GET":
        # Edit Patient
        if patient_id:
            try:
                patient = Patient.objects(patient_id=patient_id).first()
                if not patient:
                    flash(f"Patient ID {patient_id} not found.", "warning")
                    log_security(
                        f"Attempted to edit non-existent patient: {patient_id}", level=2
                    )
                    return redirect(url_for("home"))

                form = PatientForm(obj=patient)

                if is_ajax_request():
                    return render_template(
                        "patient/patient_form_fragment.html",
                        form=form,
                        patient=patient,
                        mode="edit",
                    )
                else:
                    return render_template(
                        "patient/edit_patient.html", form=form, patient=patient
                    )

            except Exception as e:
                print(f"Error fetching patient {patient_id} for edit: {e}")
                traceback.print_exc()
                log_activity(
                    f"Error loading patient {patient_id} for edit: {str(e)}", level=3
                )
                flash("Error loading patient details for editing.", "danger")
                return redirect(url_for("home"))

        # Add Patient
        else:
            form = PatientForm()
            if is_ajax_request():
                return render_template(
                    "patient/patient_form_fragment.html",
                    form=form,
                    patient=None,
                    mode="add",
                )
            else:
                return render_template("patient/add_patient.html", form=form)

    # Handle POST
    elif request.method == "POST":
        form = PatientForm()
        if not form.validate_on_submit():
            pass

        try:
            patient_id_from_form = request.form.get("patient_id")

            data = form.data

            input_features = {
                k: v
                for k, v in data.items()
                if k not in ["csrf_token", "submit", "patient_id"]
            }

            risk_percent, risk_level = stroke_predictor.predict_risk(input_features)

            is_edit = patient_id_from_form is not None and patient_id_from_form != ""

            if is_edit:
                patient = Patient.objects(patient_id=patient_id_from_form).first()
                if not patient:
                    log_activity(
                        f"Patient update attempted but not found: {patient_id_from_form}",
                        level=2,
                    )
                    return jsonify(
                        {"success": False, "message": "Patient not found for update"}
                    ), 404
            else:
                patient = Patient()
                patient.patient_id = IDGenerator.generate_id()
                patient.record_entry_date = datetime.now()
                patient.created_by = (
                    current_user.username
                )

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

            patient.stroke_risk = risk_percent
            patient.risk_level = risk_level

            patient.save()

            if is_edit:
                log_activity(
                    f"Updated patient record: {patient.patient_id} (risk={risk_percent}, level={risk_level})",
                    level=1,
                )
            else:
                log_activity(
                    f"Added new patient record: {patient.patient_id} (risk={risk_percent}, level={risk_level})",
                    level=1,
                )

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
            log_activity(f"Error processing form submission: {str(e)}", level=4)
            return jsonify(
                {
                    "success": False,
                    "message": f"Server error processing patient data: {str(e)}",
                }
            ), 500


# --- Legacy Routes ---


@patient_bp.route("/predict", methods=["POST"])
@login_required
def predict_risk():
    try:
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

        try:
            risk_percentage = float(stroke_predictor.predict_risk(prediction_data))
            risk_level = get_risk_level(risk_percentage)
            log_activity(
                f"Prediction computed (inline API): risk={risk_percentage}, level={risk_level}",
                level=1,
            )
        except ValueError as e:
            log_activity(f"Prediction failed due to bad input: {str(e)}", level=2)
            return jsonify({"success": False, "message": str(e)}), 400

        patient_id = request.form.get("patient_id")

        try:
            if patient_id:
                patient = Patient.objects(patient_id=patient_id).first()
                if not patient:
                    patient = None
            else:
                patient = None

            if patient:
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

                patient.stroke_risk = risk_percentage
                # optional — set/update audit fields if you have them
                try:
                    patient.updated_by = current_user.name
                    patient.record_last_updated = datetime.now()
                except Exception:
                    pass

                patient.save()
                response_patient = patient

                log_activity(
                    f"Updated patient via legacy /predict endpoint: {response_patient.patient_id} (risk={risk_percentage}, level={risk_level})",
                    level=1,
                )
            else:
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

                log_activity(
                    f"Created patient via legacy /predict endpoint: {response_patient.patient_id} (risk={risk_percentage}, level={risk_level})",
                    level=1,
                )

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
            log_activity(f"Error saving/updating patient: {str(e)}", level=4)
            return jsonify(
                {
                    "success": False,
                    "message": f"Error saving/updating patient data: {str(e)}",
                }
            ), 500

    except Exception as e:
        print(f"Unexpected error in predict_risk: {str(e)}")
        print(traceback.format_exc())
        log_activity(f"Unexpected error in predict_risk: {str(e)}", level=4)
        return jsonify(
            {"success": False, "message": f"An unexpected error occurred: {str(e)}"}
        ), 500


@patient_bp.route("/delete/<patient_id>", methods=["POST"])
@login_required
def delete_patient(patient_id):
    try:
        if current_user.role != "admin":
            log_security(
                f"Unauthorized delete attempt for patient {patient_id} by user {current_user.username}",
                level=3,
            )
            return jsonify(
                {
                    "success": False,
                    "message": "Unauthorized: Only admins can delete records",
                }
            ), 403

        patient = Patient.objects(patient_id=patient_id).first()
        if not patient:
            log_activity(
                f"Delete attempted for non-existent patient: {patient_id}", level=2
            )
            return jsonify({"success": False, "message": "Patient not found"}), 404

        patient.delete()

        log_security(f"Deleted patient record: {patient_id}", level=1)

        return jsonify(
            {
                "success": True,
                "message": "Patient record deleted successfully",
                "redirect": url_for("home"),
            }
        ), 200

    except Exception as e:
        print(f"Error deleting patient: {str(e)}")
        log_security(f"Error deleting patient {patient_id}: {str(e)}", level=4)
        return jsonify(
            {"success": False, "message": f"Error deleting patient: {str(e)}"}
        ), 500


@patient_bp.route("/count", methods=["GET"])
@login_required
def patients_count():
    try:
        count = Patient.objects.count()
        log_activity(f"Accessed patient count endpoint (count={count})", level=1)
        return jsonify({"count": count})
    except Exception as error:
        print("Error counting patients:", str(error))
        log_activity(f"Error counting patients: {str(error)}", level=3)
        return jsonify({"error": "Failed to count patients"}), 500
