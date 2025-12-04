# app/models/patient.py
from mongoengine import (
    Document,
    StringField,
    IntField,
    FloatField,
    DateTimeField,
)
from datetime import datetime
from app.security.AES_Encryptor import cipher_suite

# --- Custom Encrypted Fields ---

class EncryptedStringField(StringField):
    """A field that stores encrypted strings in MongoDB."""
    def to_mongo(self, value):
        if value is None: return None
        return cipher_suite.encrypt(str(value))

    def to_python(self, value):
        if value is None: return None
        return cipher_suite.decrypt(value)

class EncryptedIntField(StringField):
    """A field that stores encrypted integers as strings in MongoDB."""
    def validate(self, value):
        if not isinstance(value, (int, str)):
            self.error("Value must be an integer or encrypted string.")

    def to_mongo(self, value):
        if value is None: return None
        return cipher_suite.encrypt(str(value))

    def to_python(self, value):
        if value is None: return None
        # Handle cases where value might be float/int from legacy data
        if isinstance(value, (int, float)):
            return int(value)
        
        # Use the robust decrypt method from cipher_suite
        decrypted = cipher_suite.decrypt(value)
        try:
            return int(decrypted)
        except (ValueError, TypeError):
            # If it's still not an int (could be a legacy string that's not a number)
            try:
                return int(float(decrypted)) # Handle "55.0"
            except:
                return 0

class EncryptedFloatField(StringField):
    """A field that stores encrypted floats as strings in MongoDB."""
    def validate(self, value):
        if not isinstance(value, (int, float, str)):
            self.error("Value must be a number or encrypted string.")

    def to_mongo(self, value):
        if value is None: return None
        return cipher_suite.encrypt(str(value))

    def to_python(self, value):
        if value is None: return None
        # Handle cases where value might be float/int from legacy data
        if isinstance(value, (int, float)):
            return float(value)
            
        decrypted = cipher_suite.decrypt(value)
        try:
            return float(decrypted)
        except (ValueError, TypeError):
            return 0.0

class Patient(Document):
    # Demographics
    patient_id = StringField(required=True, unique=True, min_length=9, max_length=9) # Plain for Search
    name = StringField(required=True) # Plain for Search
    age = EncryptedIntField(required=True)
    gender = EncryptedStringField(required=True, choices=["Male", "Female", "Other"])

    # Medical & Lifestyle
    ever_married = EncryptedStringField(required=True, choices=["Yes", "No"])
    work_type = EncryptedStringField(
        required=True,
        choices=["Children", "Govt Job", "Never Worked", "Private", "Self-Employed"],
    )
    residence_type = EncryptedStringField(required=True, choices=["Rural", "Urban"])
    heart_disease = EncryptedStringField(required=True, choices=["Yes", "No"])
    hypertension = EncryptedStringField(required=True, choices=["Yes", "No"])

    # Health Metrics
    avg_glucose_level = FloatField(required=True, min_value=0) # Plain for Stats/Sorting
    bmi = EncryptedFloatField(required=True)
    smoking_status = EncryptedStringField(
        required=True, choices=["Smokes", "Formerly Smoked", "Never Smoked", "Unknown"]
    )
    stroke_risk = FloatField(required=True, min_value=0, max_value=100) # Plain for Stats/Sorting

    # Metadata
    record_entry_date = DateTimeField(default=datetime.now, required=True)
    created_by = StringField(required=True)
    updated_at = DateTimeField()
    updated_by = StringField()

    meta = {
        "collection": "patients",
        "ordering": ["-record_entry_date"],
        "indexes": [
            {"fields": ["patient_id"], "unique": True},
            {"fields": ["$name"], "default_language": "english"},
        ],
    }
