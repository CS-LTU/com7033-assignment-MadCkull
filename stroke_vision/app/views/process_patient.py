# views/process_patient.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
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


@patient_bp.route("/add", methods=["GET"])
@login_required
def add_patient():
    form = PatientForm()
    return render_template("patient/add_patient.html", form=form)


@patient_bp.route("/predict", methods=["POST"])
@login_required
def predict_risk():
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

    # show list of patients


@patient_bp.route("/edit/<patient_id>", methods=["GET", "POST"])
@login_required
def edit_patient(patient_id):
    patient = Patient.objects(patient_id=patient_id).first()
    if not patient:
        flash("Patient not found", "warning")
        return redirect(url_for("home"))

    form = PatientForm(obj=patient)  # Prefill form with patient data

    if request.method == "POST":
        # Update patient data from form
        try:
            patient.name = form.name.data
            patient.age = form.age.data
            patient.gender = form.gender.data
            patient.ever_married = form.ever_married.data
            patient.work_type = map_work_type(form.work_type.data)
            patient.residence_type = form.residence_type.data
            patient.heart_disease = map_binary_to_yes_no(form.heart_disease.data)
            patient.hypertension = map_binary_to_yes_no(form.hypertension.data)
            patient.avg_glucose_level = float(form.avg_glucose_level.data)
            patient.bmi = float(form.bmi.data)
            patient.smoking_status = map_smoking_status(form.smoking_status.data)

            patient.save()
            flash("Patient updated successfully", "success")
            return redirect(url_for("home"))
        except Exception as e:
            flash(f"Error updating patient: {str(e)}", "danger")

    return render_template("patient/edit_patient.html", form=form, patient=patient)


@patient_bp.route("/delete/<patient_id>", methods=["POST"])
@login_required
def delete_patient(patient_id):
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
    try:
        count = Patient.objects.count()
        return jsonify({"count": count})
    except Exception as error:
        print("Error counting patients:", str(error))
        return jsonify({"error": "Failed to count patients"}), 500
