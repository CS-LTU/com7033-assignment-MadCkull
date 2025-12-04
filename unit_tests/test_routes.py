# unit_tests/test_routes.py
import pytest
from flask import url_for


def test_home_page(client):
    """Test that the home page loads correctly."""
    response = client.get('/', follow_redirects=True)
    assert response.status_code == 200
    # Home page redirects to login if not authenticated
    assert b"StrokeVision" in response.data or b"Login" in response.data


def test_dashboard_access_protected(client):
    """Test that dashboard requires login."""
    response = client.get('/dashboard/view', follow_redirects=True)
    assert response.status_code == 200
    assert b"Login" in response.data or b"Please log in" in response.data or b"Sign In" in response.data


def test_dashboard_access_authorized(client, doctor_user):
    """Test that logged-in Doctor can access dashboard."""
    # Login as Doctor (required role for dashboard)
    client.post('/auth/login', data={
        'email': 'doctor@example.com',
        'password': 'DoctorPass123!'
    }, follow_redirects=True)
    
    response = client.get('/dashboard/view', follow_redirects=True)
    assert response.status_code == 200


def test_dashboard_stats_api(client, doctor_user):
    """Test the dashboard stats API."""
    client.post('/auth/login', data={
        'email': 'doctor@example.com',
        'password': 'DoctorPass123!'
    }, follow_redirects=True)
    
    response = client.get('/dashboard/api/stats')
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['success'] is True
    assert 'kpis' in json_data


def test_patient_list_view_access(client, doctor_user):
    """Test that logged-in Doctor can access patient list view."""
    client.post('/auth/login', data={
        'email': 'doctor@example.com',
        'password': 'DoctorPass123!'
    }, follow_redirects=True)

    # Patient list requires Doctor role and AJAX header
    response = client.get('/patient/views/list', headers={'X-Requested-With': 'XMLHttpRequest'})
    assert response.status_code == 200


def test_nurse_cannot_access_patient_list(client, test_user):
    """Test that Nurse role cannot access patient list (Doctor only)."""
    client.post('/auth/login', data={
        'email': 'test@example.com',
        'password': 'TestPass123!'
    }, follow_redirects=True)

    response = client.get('/patient/views/list', headers={'X-Requested-With': 'XMLHttpRequest'})
    assert response.status_code == 403


def test_unauthenticated_api_access(client):
    """Test that unauthenticated users cannot access protected APIs."""
    response = client.get('/patient/api/data', headers={'X-Requested-With': 'XMLHttpRequest'})
    # Should redirect to login or return 401
    assert response.status_code in [401, 302]
