# app/security/input_sanitizer.py
import re
from html import escape


class ValidationError(Exception):
    """Raised when input validation fails. Contains user-friendly error message."""
    pass


class InputSanitizer:
    """
    Utility to sanitize and validate user inputs before they reach the DB layer.
    All validation methods raise ValidationError on failure for clean rejection handling.
    """

    # Fields that should never be sanitized (passwords need special chars)
    SKIP_SANITIZE_FIELDS = {"password", "current_password", "new_password", "confirm_password"}

    # Patient field allowed values (must match model/form exactly)
    ALLOWED_GENDERS = {"Male", "Female", "Other"}
    ALLOWED_MARRIED = {"Yes", "No"}
    ALLOWED_RESIDENCE = {"Urban", "Rural"}
    ALLOWED_WORK_TYPES = {"Private", "Self-employed", "Govt_job", "children", "Never_worked"}
    ALLOWED_SMOKING = {"formerly smoked", "never smoked", "smokes", "Unknown"}
    ALLOWED_BINARY = {"0", "1"}

    # Regex patterns
    NAME_PATTERN = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ'\-.\s]{0,98}[A-Za-zÀ-ÖØ-öø-ÿ.]?$")
    PATIENT_ID_PATTERN = re.compile(r"^\d{9}$")

    @staticmethod
    def sanitize_text(text):
        """
        Cleans plain text input.
        - Strips whitespace
        - Escapes HTML entities to prevent stored XSS
        """
        if not isinstance(text, str):
            return text
        
        cleaned = text.strip()
        cleaned = escape(cleaned)
        
        return cleaned

    @staticmethod
    def validate_mongo_input(data):
        """
        Recursively validates input dictionary for MongoDB operations.
        - Blocks operator injection (keys starting with $)
        - Ensures keys don't contain forbidden characters
        - Blocks null bytes and command patterns
        """
        if isinstance(data, dict):
            for key, value in data.items():
                if key.startswith("$"):
                    raise ValidationError("Invalid input detected.")
                
                if "." in key:
                    raise ValidationError("Invalid input detected.")
                
                if "\x00" in key:
                    raise ValidationError("Invalid input detected.")
                    
                InputSanitizer.validate_mongo_input(value)
                
        elif isinstance(data, list):
            for item in data:
                InputSanitizer.validate_mongo_input(item)
        
        elif isinstance(data, str):
            if "\x00" in data:
                raise ValidationError("Invalid input detected.")
                
        return True

    @staticmethod
    def clean_form_data(form_data, skip_fields=None):
        """
        Sanitizes an entire ImmutableMultiDict or dict from request.form/json.
        Skips password fields and any custom skip_fields.
        Returns a clean dictionary.
        """
        skip = InputSanitizer.SKIP_SANITIZE_FIELDS.copy()
        if skip_fields:
            skip.update(skip_fields)
        
        clean_data = {}
        for key, value in form_data.items():
            if key in skip:
                clean_data[key] = value
            else:
                clean_data[key] = InputSanitizer.sanitize_text(value)
        return clean_data

    @staticmethod
    def validate_patient_id(patient_id):
        """Validates patient ID format (exactly 9 digits)."""
        if not patient_id or not InputSanitizer.PATIENT_ID_PATTERN.match(str(patient_id)):
            raise ValidationError("Invalid patient ID.")
        return True

    @staticmethod
    def validate_name(name):
        """Validates patient name."""
        if not name or not isinstance(name, str):
            raise ValidationError("Name is required.")
        
        name = name.strip()
        
        if len(name) < 2:
            raise ValidationError("Name is too short.")
        
        if len(name) > 100:
            raise ValidationError("Name is too long.")
        
        if not InputSanitizer.NAME_PATTERN.match(name):
            raise ValidationError("Please enter a valid name.")
        
        return True

    @staticmethod
    def validate_age(age):
        """Validates age is an integer between 10 and 120."""
        try:
            age_int = int(age)
        except (ValueError, TypeError):
            raise ValidationError("Please enter a valid age.")
        
        if age_int < 10 or age_int > 120:
            raise ValidationError("Please enter a valid age (10-120).")
        
        return True

    @staticmethod
    def validate_gender(gender):
        """Validates gender is exactly Male, Female, or Other (case-sensitive)."""
        if gender not in InputSanitizer.ALLOWED_GENDERS:
            raise ValidationError("Please select a valid gender.")
        return True

    @staticmethod
    def validate_numeric_field(value, field_name, min_val=0, max_val=None):
        """Validates a numeric field is within range."""
        try:
            num = float(value)
        except (ValueError, TypeError):
            raise ValidationError(f"Please enter a valid {field_name.lower()}.")
        
        if num < min_val:
            raise ValidationError(f"{field_name} value is too low.")
        
        if max_val is not None and num > max_val:
            raise ValidationError(f"{field_name} value is too high.")
        
        return True

    @staticmethod
    def validate_select_field(value, allowed_values, field_name):
        """Validates a select field value is in the allowed set."""
        if value not in allowed_values:
            raise ValidationError(f"Please select a valid {field_name.lower()}.")
        return True

    @staticmethod
    def validate_patient_data(data):
        """
        Comprehensive validation for patient form data.
        Raises ValidationError if any field is invalid.
        Returns True if all validations pass.
        """
        # Required field checks
        required_fields = ["name", "age", "gender", "ever_married", "work_type", 
                          "residence_type", "heart_disease", "hypertension",
                          "avg_glucose_level", "bmi", "smoking_status"]
        
        for field in required_fields:
            if field not in data or data.get(field) in [None, ""]:
                friendly_name = field.replace('_', ' ').title()
                raise ValidationError(f"{friendly_name} is required.")

        # Individual field validations
        InputSanitizer.validate_name(data.get("name"))
        InputSanitizer.validate_age(data.get("age"))
        InputSanitizer.validate_gender(data.get("gender"))
        
        InputSanitizer.validate_select_field(
            data.get("ever_married"), 
            InputSanitizer.ALLOWED_MARRIED, 
            "marital status"
        )
        
        InputSanitizer.validate_select_field(
            data.get("residence_type"), 
            InputSanitizer.ALLOWED_RESIDENCE, 
            "residence type"
        )
        
        InputSanitizer.validate_select_field(
            data.get("work_type"), 
            InputSanitizer.ALLOWED_WORK_TYPES, 
            "work type"
        )
        
        InputSanitizer.validate_select_field(
            data.get("heart_disease"), 
            InputSanitizer.ALLOWED_BINARY, 
            "heart disease option"
        )
        
        InputSanitizer.validate_select_field(
            data.get("hypertension"), 
            InputSanitizer.ALLOWED_BINARY, 
            "hypertension option"
        )
        
        InputSanitizer.validate_select_field(
            data.get("smoking_status"), 
            InputSanitizer.ALLOWED_SMOKING, 
            "smoking status"
        )
        
        # Numeric fields with realistic medical limits
        InputSanitizer.validate_numeric_field(
            data.get("avg_glucose_level"), 
            "Glucose level", 
            min_val=0, 
            max_val=600
        )
        
        InputSanitizer.validate_numeric_field(
            data.get("bmi"), 
            "BMI", 
            min_val=0, 
            max_val=100
        )
        
        return True
