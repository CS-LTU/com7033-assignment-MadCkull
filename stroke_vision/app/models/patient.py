# app/models/patient.py
from mongoengine import (
    Document,
    StringField,
    IntField,
    FloatField,
    DateTimeField,
)
from datetime import datetime


class Patient(Document):
    # Identification and Demographic Information
    # NOTE: use min_length/max_length for strings
    patient_id = StringField(required=True, unique=True, min_length=9, max_length=9)
    name = StringField(required=True)
    age = IntField(required=True, min_value=5, max_value=120)
    gender = StringField(required=True, choices=["Male", "Female", "Other"])

    # Medical and Lifestyle Information
    ever_married = StringField(required=True, choices=["Yes", "No"])
    work_type = StringField(
        required=True,
        choices=["Children", "Govt Job", "Never Worked", "Private", "Self-Employed"],
    )
    residence_type = StringField(required=True, choices=["Rural", "Urban"])
    heart_disease = StringField(required=True, choices=["Yes", "No"])
    hypertension = StringField(required=True, choices=["Yes", "No"])

    # Health Metrics
    avg_glucose_level = FloatField(required=True, min_value=0)
    bmi = FloatField(required=True, min_value=0)
    smoking_status = StringField(
        required=True, choices=["Smokes", "Formerly Smoked", "Never Smoked", "Unknown"]
    )
    stroke_risk = FloatField(required=True, min_value=0, max_value=100)

    # Metadata
    record_entry_date = DateTimeField(default=datetime.now, required=True)
    created_by = StringField(required=True)
    updated_at = DateTimeField()
    updated_by = StringField()

    meta = {
        "collection": "patients",
        "ordering": ["-record_entry_date"],
        # indexes: unique patient_id and a text index on name for searches
        "indexes": [
            {"fields": ["patient_id"], "unique": True},
            # Text index on name for free-text; also helpful for case-insensitive prefix queries
            {"fields": ["$name"], "default_language": "english"},
        ],
    }
