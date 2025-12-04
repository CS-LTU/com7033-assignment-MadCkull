# tests/conftest.py
import os
import sys
import pytest
from mongoengine import connect, disconnect
import mongomock
from datetime import datetime
import pickle
from pathlib import Path
import tensorflow as tf

# Add the project root and stroke_vision directory to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../stroke_vision')))

from app import create_app, db
from app.models.user import User


# MongoDB Mock Database Setup  --------------------------------
@pytest.fixture(scope="function", autouse=True)
def setup_db():
    """Setup test database before each test"""
    disconnect()  # Disconnect any existing connections
    connect(
        "testdb", host="mongodb://localhost", mongo_client_class=mongomock.MongoClient
    )
    yield
    disconnect()  # Cleanup after test


# Model Evaluation Tests -----------------------------------
@pytest.fixture
def model():
    """Load the trained model"""
    # Assuming project structure: project_root/tests/conftest.py
    # and project_root/stroke_vision/app/static/models/...
    root_dir = Path(__file__).parent.parent
    model_path = root_dir / "stroke_vision" / "app" / "static" / "models" / "stroke_vision_model_Best.keras"
    # Fallback for different structure if needed, but this matches observed structure
    if not model_path.exists():
         # Try without stroke_vision prefix if app is top level? But we saw it is nested.
         pass
    return tf.keras.models.load_model(model_path)


@pytest.fixture
def preprocessors():
    """Load the preprocessors"""
    root_dir = Path(__file__).parent.parent
    preprocessor_path = root_dir / "stroke_vision" / "app" / "static" / "models" / "preprocessors.pkl"
    with open(preprocessor_path, "rb") as f:
        return pickle.load(f)


@pytest.fixture
def test_data():
    """Test dataset for model evaluation"""
    return {
        "gender": "Male",
        "age": 75,
        "hypertension": 1,
        "heart_disease": 1,
        "ever_married": "Yes",
        "Residence_type": "Urban",
        "avg_glucose_level": 210,
        "bmi": 32.5,
        "work_type": "Private",
        "smoking_status": "smokes",
    }


# Patient Prediction Tests  --------------------------------
@pytest.fixture
def high_risk_patient():
    return {
        "gender": "Male",
        "age": "75",
        "hypertension": "1",
        "heart_disease": "1",
        "ever_married": "Yes",
        "residence_type": "Urban",
        "avg_glucose_level": "210",
        "bmi": "32.5",
        "work_type": "Private",
        "smoking_status": "smokes",
    }


@pytest.fixture
def low_risk_patient():
    return {
        "gender": "Female",
        "age": "17",
        "hypertension": "0",
        "heart_disease": "0",
        "ever_married": "No",
        "residence_type": "Urban",
        "avg_glucose_level": "85",
        "bmi": "22.1",
        "work_type": "Private",
        "smoking_status": "never smoked",
    }


@pytest.fixture
def invalid_patient():
    return {
        "gender": "Male",
        "age": "150",  # Invalid age
        "hypertension": "1",
        "heart_disease": "0",
        "ever_married": "Yes",
        "residence_type": "Urban",
        "avg_glucose_level": "85",
        "bmi": "22.1",
        "work_type": "Private",
        "smoking_status": "never smoked",
    }


# ID Generation Tests --------------------------------
from datetime import datetime


@pytest.fixture
def current_date_portion():
    """Returns the expected date portion of the ID based on current date"""
    now = datetime.now()
    return f"{str(now.year)[-1]}{str(now.month).zfill(2)}{str(now.day).zfill(2)}"


@pytest.fixture
def sample_valid_id(current_date_portion):
    """Returns a valid ID format for testing"""
    return f"{current_date_portion}1234"


@pytest.fixture
def sample_invalid_ids():
    """Returns a list of invalid IDs for testing"""
    return [
        "12345",  # Too short
        "1234567890",  # Too long
        "abcdefghi",  # Non-numeric
        None,  # None value
        "923456789",  # Invalid month (23)
        "913456789",  # Invalid day (34)
        "000000000",  # All zeros
    ]


# User Authentication, Login, Registration Tests --------------------------------


@pytest.fixture
def app():
    """Create application for the tests."""
    app = create_app()
    app.config.update(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "SECRET_KEY": "test-secret-key",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        }
    )
    return app


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def _db(app):
    """Create and initialize test database."""
    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()


@pytest.fixture
def test_user(app, _db):
    """Create a test user."""
    with app.app_context():
        user = User(name="Test User", email="test@example.com", role="Nurse")
        user.set_password("TestPass123!")  # Meets complexity: Upper, Lower, Number, Special
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def doctor_user(app, _db):
    """Create a test user with Doctor role for protected routes."""
    with app.app_context():
        user = User(name="Doctor User", email="doctor@example.com", role="Doctor")
        user.set_password("DoctorPass123!")
        db.session.add(user)
        db.session.commit()
        return user

