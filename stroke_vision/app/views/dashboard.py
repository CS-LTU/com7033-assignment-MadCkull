# app/views/dashboard.py
from flask import Blueprint, abort, render_template, jsonify
from flask_login import login_required, current_user
from app.models.patient import Patient
from app.utils.log_utils import log_activity, log_security
from app.security.auth_shield import AuthShield

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard/view", methods=["GET"])
@login_required
def view_dashboard():
    """Renders the dashboard HTML fragment."""
    if current_user.role not in ["Admin", "Doctor", "Nurse"]:
        abort(403)
    return render_template("toolbar/dashboard.html")


@dashboard_bp.route("/dashboard/api/stats", methods=["GET"])
@login_required
def get_dashboard_stats():
    """
    Aggregates patient data for the dashboard charts and KPIs.
    Optimized for MongoDB/MongoEngine.
    """
    try:
        if current_user.role not in ["Admin", "Doctor", "Nurse"]:
            return jsonify({"success": False, "message": "Access denied."}), 403

        # 1. Fetch patients
        # We fetch all because we need them for scatter plot and stats on encrypted fields
        patients = list(Patient.objects())
        total_patients = len(patients)

        high_risk_count = 0
        smokers_count = 0
        total_glucose = 0
        work_counts = {}
        scatter_data = []

        for p in patients:
            # 2. KPI & Stat Calculations (Python-side due to encryption)
            if p.stroke_risk > 20:
                high_risk_count += 1
            
            if p.smoking_status in ["Smokes", "Formerly Smoked"]:
                smokers_count += 1
            
            total_glucose += p.avg_glucose_level

            # Work Type Distribution
            w_type = p.work_type
            work_counts[w_type] = work_counts.get(w_type, 0) + 1

            # Scatter Plot Data
            scatter_data.append({
                "x": p.bmi,
                "y": p.avg_glucose_level,
                "r": round(p.stroke_risk / 8, 2),
                "risk": round(p.stroke_risk, 2),
            })

        # Calculate Average Glucose
        avg_glucose = round(total_glucose / total_patients, 2) if total_patients > 0 else 0

        # 3. Top 5 High Risk Patients
        # stroke_risk is plain, so sorting still works at DB level
        top_risk_patients = Patient.objects.order_by("-stroke_risk").limit(5)
        risk_table_data = []

        for p in top_risk_patients:
            conditions = []
            if p.hypertension == "Yes":
                conditions.append("Hypertension")
            if p.heart_disease == "Yes":
                conditions.append("Heart Disease")
            condition_str = ", ".join(conditions) if conditions else "None"

            # Mask name for Admin and Nurse roles for privacy
            p_name = p.name
            if current_user.role in ["Admin", "Nurse"]:
                p_name = AuthShield.mask_name(p_name)

            risk_table_data.append({
                "name": p_name,
                "age": p.age,
                "gender": p.gender,
                "conditions": condition_str,
                "avg_glucose_level": p.avg_glucose_level,
                "stroke_risk": round(p.stroke_risk, 2),
            })

        log_activity(f"Requested dashboard stats.", level=2)

        return jsonify({
            "success": True,
            "kpis": {
                "total": total_patients,
                "high_risk": high_risk_count,
                "avg_glucose": avg_glucose,
                "smokers": smokers_count,
            },
            "charts": {"scatter": scatter_data, "work_distribution": work_counts},
            "table": risk_table_data,
        })

    except Exception as e:
        # Log both as an activity error (so doctors/admins see the failure) and as a security-level alert for admins.
        err_msg = f"Dashboard stats generation failed: {type(e).__name__}: {e}"

        # Activity log at highest severity to indicate operation failure (patient-related).
        log_activity(err_msg, level=4)

        # Security log to ensure admins get visibility for investigation.
        log_security(f"Dashboard API error encountered. {err_msg}", level=4)

        print(f"Dashboard Error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
