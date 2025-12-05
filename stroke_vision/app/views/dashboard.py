# app/views/dashboard.py
from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from app.models.patient import Patient

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard/view", methods=["GET"])
@login_required
def view_dashboard():
    """Renders the dashboard HTML fragment."""
    return render_template("toolbar/dashboard.html")


@dashboard_bp.route("/dashboard/api/stats", methods=["GET"])
@login_required
def get_dashboard_stats():
    """
    Aggregates patient data for the dashboard charts and KPIs.
    Optimized for MongoDB/MongoEngine.
    """
    try:
        # 1. Fetch all patients (needed for comprehensive stats)
        # In a very large DB, you would use aggregate pipelines here instead of loading objects.
        patients = Patient.objects()

        total_patients = patients.count()

        # 2. KPI Calculations
        high_risk_count = patients.filter(stroke_risk__gt=20).count()
        # hypertensive_count = patients.filter(hypertension="Yes").count()
        smokers_count = patients.filter(
            smoking_status__in=["Smokes", "Formerly Smoked"]
        ).count()

        # Calculate Average Glucose safely
        avg_glucose = 0
        if total_patients > 0:
            total_glucose = sum(p.avg_glucose_level for p in patients)
            avg_glucose = round(total_glucose / total_patients, 2)

        # 3. Chart Data Preparation

        # Scatter Plot Data (BMI vs Glucose vs Risk)
        scatter_data = []
        for p in patients:
            scatter_data.append(
                {
                    "x": p.bmi,
                    "y": p.avg_glucose_level,
                    "r": round(p.stroke_risk / 8, 2),  # Radius scaling
                    "risk": round(p.stroke_risk, 2),  # Passed for color logic in JS
                }
            )

        # Work Type Distribution
        work_counts = {}
        # Using aggregation for better performance
        pipeline = [{"$group": {"_id": "$work_type", "count": {"$sum": 1}}}]
        work_agg = Patient.objects.aggregate(*pipeline)
        for doc in work_agg:
            work_counts[doc["_id"]] = doc["count"]

        # 4. Top 5 High Risk Patients
        # Sort by stroke_risk desc, limit 5
        top_risk_patients = Patient.objects.order_by("-stroke_risk").limit(5)
        risk_table_data = []

        for p in top_risk_patients:
            # Determine comorbidities text
            conditions = []
            if p.hypertension == "Yes":
                conditions.append("Hypertension")
            if p.heart_disease == "Yes":
                conditions.append("Heart Disease")
            condition_str = ", ".join(conditions) if conditions else "None"

            risk_table_data.append(
                {
                    "name": p.name,
                    "age": p.age,
                    "gender": p.gender,
                    "conditions": condition_str,
                    "avg_glucose_level": p.avg_glucose_level,
                    "stroke_risk": round(p.stroke_risk, 2),
                }
            )

        return jsonify(
            {
                "success": True,
                "kpis": {
                    "total": total_patients,
                    "high_risk": high_risk_count,
                    "avg_glucose": avg_glucose,
                    "smokers": smokers_count,
                },
                "charts": {"scatter": scatter_data, "work_distribution": work_counts},
                "table": risk_table_data,
            }
        )

    except Exception as e:
        print(f"Dashboard Error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
