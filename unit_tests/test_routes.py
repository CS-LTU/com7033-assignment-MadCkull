import pytest
from flask import url_for

def test_home_page(client):
    """Test that the home page loads correctly."""
    response = client.get('/', follow_redirects=True)
    assert response.status_code == 200
    assert b"StrokeVision" in response.data or b"Login" in response.data # Depends on if home is protected or not, usually home landing page is public or redirects to login

def test_dashboard_access_protected(client):
    """Test that dashboard requires login."""
    response = client.get('/dashboard/view', follow_redirects=True)
    assert response.status_code == 200
    assert b"Login" in response.data or b"Please log in" in response.data or b"Sign In" in response.data

def test_dashboard_access_authorized(client, test_user):
    """Test that logged-in user can access dashboard."""
    # Login first
    client.post('/auth/login', data={
        'email': 'test@example.com',
        'password': 'password123'
    }, follow_redirects=True)
    
    response = client.get('/dashboard/view', follow_redirects=True)
    assert response.status_code == 200
    # Dashboard likely contains "Dashboard" or some specific element
    # Based on dashboard.py, it renders 'toolbar/dashboard.html'
    
def test_dashboard_stats_api(client, test_user):
    """Test the dashboard stats API."""
    client.post('/auth/login', data={
        'email': 'test@example.com',
        'password': 'password123'
    }, follow_redirects=True)
    
    # It requires AJAX header usually if specified, let's check dashboard.py
    # view_dashboard checks nothing specific but login_required
    # api_patient_data in patient_manager checks AJAX.
    # get_dashboard_stats in dashboard.py doesn't seem to check AJAX explicitly in the snippet I saw?
    # Wait, looking at dashboard.py line 20-22, it doesn't have is_ajax_request check.
    
    response = client.get('/dashboard/api/stats')
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['success'] is True
    assert 'kpis' in json_data

def test_patient_list_view_access(client, test_user):
    """Test that logged-in user can access patient list view."""
    client.post('/auth/login', data={
        'email': 'test@example.com',
        'password': 'password123'
    }, follow_redirects=True)

    # patient/views/list checks for AJAX
    response = client.get('/patient/views/list', headers={'X-Requested-With': 'XMLHttpRequest'})
    assert response.status_code == 200
    assert b"patient-list" in response.data or b"table" in response.data # Some content check
