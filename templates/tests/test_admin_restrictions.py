import pytest
from models import User, Source
from werkzeug.security import generate_password_hash

def test_admin_blocked_from_sources(client, test_db):
    # Login as admin
    with client.session_transaction() as sess:
        sess["admin"] = True
        # Ensure NO user_id is set
        if "user_id" in sess: del sess["user_id"]

    # Try to access sources management
    res = client.get("/admin/sources", follow_redirects=False)
    
    # Should be redirected to login (or 403, but code redirects to auth.login)
    assert res.status_code == 302
    assert "/login" in res.location

def test_user_allowed_sources(client, test_db):
    # Create user
    user = User(username="source_mgr", password=generate_password_hash("pass"))
    test_db.add(user)
    test_db.commit()

    # Login as user
    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        # Ensure admin is NOT set
        if "admin" in sess: del sess["admin"]

    # Try to access sources management
    res = client.get("/admin/sources")
    assert res.status_code == 200
    assert b"Manage Sources" in res.data

def test_dashboard_no_sources_card(client, test_db):
    # Login as admin
    with client.session_transaction() as sess:
        sess["admin"] = True

    res = client.get("/admin/")
    assert res.status_code == 200
    html = res.data.decode()
    
    # "Active Sources" card should be gone
    assert "Active Sources" not in html
    # But "Total Users" should be there
    assert "Total Users" in html
