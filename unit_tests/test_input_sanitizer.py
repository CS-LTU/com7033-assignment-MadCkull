# unit_tests/test_input_sanitizer.py
"""Tests for the InputSanitizer security module."""
import pytest
from app.security.input_sanitizer import InputSanitizer, ValidationError


class TestSanitizeText:
    """Tests for text sanitization."""

    def test_strips_whitespace(self):
        """Test that whitespace is stripped from input."""
        assert InputSanitizer.sanitize_text("  hello  ") == "hello"
        assert InputSanitizer.sanitize_text("\t\ntest\n\t") == "test"

    def test_escapes_html(self):
        """Test that HTML entities are escaped."""
        assert InputSanitizer.sanitize_text("<script>") == "&lt;script&gt;"
        assert InputSanitizer.sanitize_text("a & b") == "a &amp; b"
        assert InputSanitizer.sanitize_text("\"quoted\"") == "&quot;quoted&quot;"

    def test_returns_non_strings_unchanged(self):
        """Test that non-string values are returned unchanged."""
        assert InputSanitizer.sanitize_text(123) == 123
        assert InputSanitizer.sanitize_text(None) is None
        assert InputSanitizer.sanitize_text(True) is True


class TestValidateMongoInput:
    """Tests for MongoDB input validation."""

    def test_blocks_operator_injection(self):
        """Test that MongoDB operator injection is blocked."""
        with pytest.raises(ValidationError) as exc:
            InputSanitizer.validate_mongo_input({"$gt": 0})
        assert "invalid" in str(exc.value).lower()

    def test_blocks_nested_operator_injection(self):
        """Test that nested operator injection is blocked."""
        with pytest.raises(ValidationError):
            InputSanitizer.validate_mongo_input({"field": {"$ne": None}})

    def test_blocks_dots_in_keys(self):
        """Test that keys with dots are blocked."""
        with pytest.raises(ValidationError):
            InputSanitizer.validate_mongo_input({"some.field": "value"})

    def test_blocks_null_bytes(self):
        """Test that null bytes are blocked."""
        with pytest.raises(ValidationError):
            InputSanitizer.validate_mongo_input({"field": "value\x00"})

    def test_allows_valid_input(self):
        """Test that valid input passes validation."""
        valid_data = {
            "name": "John Doe",
            "age": 30,
            "items": ["a", "b", "c"]
        }
        assert InputSanitizer.validate_mongo_input(valid_data) is True


class TestCleanFormData:
    """Tests for form data cleaning."""

    def test_sanitizes_text_fields(self):
        """Test that text fields are sanitized."""
        form_data = {
            "name": "  <script>Test</script>  ",
            "email": "test@example.com"
        }
        clean = InputSanitizer.clean_form_data(form_data)
        assert clean["name"] == "&lt;script&gt;Test&lt;/script&gt;"

    def test_skips_password_fields(self):
        """Test that password fields are not sanitized."""
        form_data = {
            "password": "P@ss<word>123!",
            "new_password": "New<Pass>123!",
            "confirm_password": "Confirm<Pass>123!"
        }
        clean = InputSanitizer.clean_form_data(form_data)
        assert clean["password"] == "P@ss<word>123!"
        assert clean["new_password"] == "New<Pass>123!"


class TestValidatePatientId:
    """Tests for patient ID validation."""

    def test_valid_patient_id(self):
        """Test that valid 9-digit IDs pass."""
        assert InputSanitizer.validate_patient_id("123456789") is True
        assert InputSanitizer.validate_patient_id("000000001") is True

    def test_rejects_short_id(self):
        """Test that short IDs are rejected."""
        with pytest.raises(ValidationError):
            InputSanitizer.validate_patient_id("12345")

    def test_rejects_long_id(self):
        """Test that long IDs are rejected."""
        with pytest.raises(ValidationError):
            InputSanitizer.validate_patient_id("1234567890")

    def test_rejects_non_numeric_id(self):
        """Test that non-numeric IDs are rejected."""
        with pytest.raises(ValidationError):
            InputSanitizer.validate_patient_id("abcdefghi")


class TestValidateName:
    """Tests for name validation."""

    def test_valid_names(self):
        """Test that valid names pass."""
        assert InputSanitizer.validate_name("John Doe") is True
        assert InputSanitizer.validate_name("Mary-Jane O'Connor") is True
        assert InputSanitizer.validate_name("Dr. Smith Jr.") is True
        assert InputSanitizer.validate_name("José García") is True

    def test_rejects_too_short(self):
        """Test that names shorter than 2 chars are rejected."""
        with pytest.raises(ValidationError) as exc:
            InputSanitizer.validate_name("A")
        assert "short" in str(exc.value).lower()

    def test_rejects_too_long(self):
        """Test that names longer than 100 chars are rejected."""
        long_name = "A" * 101
        with pytest.raises(ValidationError) as exc:
            InputSanitizer.validate_name(long_name)
        assert "long" in str(exc.value).lower()

    def test_rejects_special_characters(self):
        """Test that special characters are rejected."""
        with pytest.raises(ValidationError):
            InputSanitizer.validate_name("<script>alert(1)</script>")

    def test_rejects_sql_injection(self):
        """Test that SQL injection attempts are rejected."""
        with pytest.raises(ValidationError):
            InputSanitizer.validate_name("'; DROP TABLE users; --")


class TestValidateAge:
    """Tests for age validation."""

    def test_valid_ages(self):
        """Test that valid ages pass."""
        assert InputSanitizer.validate_age(25) is True
        assert InputSanitizer.validate_age("50") is True
        assert InputSanitizer.validate_age(10) is True
        assert InputSanitizer.validate_age(120) is True

    def test_rejects_too_young(self):
        """Test that ages below 10 are rejected."""
        with pytest.raises(ValidationError) as exc:
            InputSanitizer.validate_age(5)
        assert "valid age" in str(exc.value).lower()

    def test_rejects_too_old(self):
        """Test that ages above 120 are rejected."""
        with pytest.raises(ValidationError):
            InputSanitizer.validate_age(150)

    def test_rejects_non_numeric(self):
        """Test that non-numeric ages are rejected."""
        with pytest.raises(ValidationError):
            InputSanitizer.validate_age("twenty")


class TestValidateGender:
    """Tests for gender validation."""

    def test_valid_genders(self):
        """Test that valid genders pass."""
        assert InputSanitizer.validate_gender("Male") is True
        assert InputSanitizer.validate_gender("Female") is True
        assert InputSanitizer.validate_gender("Other") is True

    def test_rejects_wrong_case(self):
        """Test that incorrect case is rejected (case-sensitive)."""
        with pytest.raises(ValidationError):
            InputSanitizer.validate_gender("male")
        with pytest.raises(ValidationError):
            InputSanitizer.validate_gender("FEMALE")

    def test_rejects_invalid_values(self):
        """Test that invalid values are rejected."""
        with pytest.raises(ValidationError):
            InputSanitizer.validate_gender("Unknown")


class TestValidatePatientData:
    """Tests for comprehensive patient data validation."""

    @pytest.fixture
    def valid_patient_data(self):
        """Fixture providing valid patient data."""
        return {
            "name": "John Doe",
            "age": "45",
            "gender": "Male",
            "ever_married": "Yes",
            "work_type": "Private",
            "residence_type": "Urban",
            "heart_disease": "0",
            "hypertension": "1",
            "avg_glucose_level": "120.5",
            "bmi": "25.3",
            "smoking_status": "never smoked"
        }

    def test_valid_patient_data_passes(self, valid_patient_data):
        """Test that valid patient data passes all validations."""
        assert InputSanitizer.validate_patient_data(valid_patient_data) is True

    def test_missing_required_field_fails(self, valid_patient_data):
        """Test that missing required fields are caught."""
        del valid_patient_data["name"]
        with pytest.raises(ValidationError) as exc:
            InputSanitizer.validate_patient_data(valid_patient_data)
        assert "required" in str(exc.value).lower()

    def test_invalid_age_fails(self, valid_patient_data):
        """Test that invalid age is caught."""
        valid_patient_data["age"] = "150"
        with pytest.raises(ValidationError):
            InputSanitizer.validate_patient_data(valid_patient_data)

    def test_invalid_gender_fails(self, valid_patient_data):
        """Test that invalid gender is caught."""
        valid_patient_data["gender"] = "invalid"
        with pytest.raises(ValidationError):
            InputSanitizer.validate_patient_data(valid_patient_data)

    def test_invalid_bmi_fails(self, valid_patient_data):
        """Test that out-of-range BMI is caught."""
        valid_patient_data["bmi"] = "150"  # BMI max is 100
        with pytest.raises(ValidationError):
            InputSanitizer.validate_patient_data(valid_patient_data)

    def test_invalid_glucose_fails(self, valid_patient_data):
        """Test that out-of-range glucose is caught."""
        valid_patient_data["avg_glucose_level"] = "700"  # Max is 600
        with pytest.raises(ValidationError):
            InputSanitizer.validate_patient_data(valid_patient_data)

    def test_xss_in_name_fails(self, valid_patient_data):
        """Test that XSS attempt in name is caught."""
        valid_patient_data["name"] = "<script>alert('xss')</script>"
        with pytest.raises(ValidationError):
            InputSanitizer.validate_patient_data(valid_patient_data)
