# unit_tests/test_auth.py
from app import db, bcrypt
from app.models.user import User


class TestRegistration:
    def test_register_new_user_with_valid_form(self, app, client, _db):
        """Test user registration with valid form data."""
        with app.app_context():
            test_user_data = {
                "name": "Test User",
                "email": "newuser@example.com",
                "password": "SecurePass123!",  # Meets complexity requirements
                "role": "Nurse",  # Correct case
            }

            response = client.post(
                "/auth/register", data=test_user_data, follow_redirects=False
            )

            assert response.status_code == 302
            assert "/auth/login" in response.headers.get("Location", "")

            user = User.query.filter_by(email="newuser@example.com").first()
            assert user is not None
            assert user.name == "Test User"
            assert user.role == "Nurse"
            assert bcrypt.check_password_hash(user.password, "SecurePass123!")

    def test_register_existing_user(self, app, client, _db):
        """Test registration with an email that already exists."""
        with app.app_context():
            existing_user = User(
                name="Existing User", email="existing@example.com", role="Nurse"
            )
            existing_user.set_password("ExistingPass123!")
            db.session.add(existing_user)
            db.session.commit()

            test_user_data = {
                "name": "New User",
                "email": "existing@example.com",
                "password": "NewPass123!",
                "role": "Nurse",
            }

            response = client.post(
                "/auth/register", data=test_user_data, follow_redirects=True
            )

            # Flash message: "This email is already registered."
            assert b"already registered" in response.data

    def test_register_with_invalid_form(self, app, client, _db):
        """Test registration with invalid form data."""
        with app.app_context():
            test_user_data = {
                "name": "",
                "email": "invalid-email",
                "password": "short",
                "role": "invalid_role",
            }

            response = client.post(
                "/auth/register", data=test_user_data, follow_redirects=True
            )

            assert response.status_code == 200
            assert User.query.count() == 0


class TestLogin:
    def test_successful_login(self, app, client, test_user):
        """Test successful user login."""
        with app.app_context():
            response = client.post(
                "/auth/login",
                data={"email": "test@example.com", "password": "TestPass123!"},
                follow_redirects=True,
            )

            # Login success redirects to home page (no flash message is shown)
            assert response.status_code == 200
            # Check we're on home page (not login page)
            assert b"StrokeVision" in response.data

    def test_login_with_incorrect_password(self, app, client, test_user):
        """Test login with incorrect password."""
        with app.app_context():
            response = client.post(
                "/auth/login",
                data={"email": "test@example.com", "password": "WrongPassword123!"},
                follow_redirects=True,
            )

            assert response.status_code == 200
            assert b"Invalid email or password" in response.data

    def test_login_with_non_existent_user(self, app, client, _db):
        """Test login with non-existent user."""
        with app.app_context():
            response = client.post(
                "/auth/login",
                data={"email": "nonexistent@example.com", "password": "SomePass123!"},
                follow_redirects=True,
            )

            assert response.status_code == 200
            assert b"Invalid email or password" in response.data

    def test_login_with_invalid_form(self, app, client, _db):
        """Test login with invalid form data."""
        with app.app_context():
            response = client.post(
                "/auth/login",
                data={"email": "invalid-email", "password": "short"},
                follow_redirects=True,
            )

            assert response.status_code == 200
            assert b"Login" in response.data  # Verify we're on the login page


class TestPasswordHashing:
    def test_password_hashing(self, app, _db):
        """Test password hashing functionality."""
        with app.app_context():
            user = User(name="Test User", email="hash@example.com", role="Nurse")

            original_password = "TestPassword123!"
            user.set_password(original_password)

            # Ensure password is hashed
            assert user.password != original_password
            assert isinstance(user.password, str)
            assert len(user.password) > 20

            # Test password verification
            assert user.check_password(original_password) is True
            assert user.check_password("wrong_password") is False

    def test_password_hashing_different_users(self, app, _db):
        """Test that same password generates different hashes for different users."""
        with app.app_context():
            password = "SamePassword123!"

            user1 = User(name="User1", email="user1@example.com", role="Nurse")
            user2 = User(name="User2", email="user2@example.com", role="Nurse")

            user1.set_password(password)
            user2.set_password(password)

            # Ensure different users get different password hashes
            assert user1.password != user2.password
            # But both can still verify the password
            assert user1.check_password(password) is True
            assert user2.check_password(password) is True

    def test_password_unicode_support(self, app, _db):
        """Test password hashing with Unicode characters."""
        with app.app_context():
            user = User(name="Test User", email="unicode@example.com", role="Nurse")
            unicode_password = "Пароль123!"  # Russian characters with complexity

            user.set_password(unicode_password)
            assert user.check_password(unicode_password) is True
            assert user.check_password("wrong_password") is False


class TestLogout:
    def test_logout(self, app, client, test_user):
        """Test user logout functionality."""
        with app.app_context():
            # First login
            client.post(
                "/auth/login",
                data={"email": "test@example.com", "password": "TestPass123!"},
            )

            # Then logout
            response = client.get("/auth/logout", follow_redirects=True)

            assert response.status_code == 200
            # Flash message: "You have been logged out."
            assert b"logged out" in response.data
