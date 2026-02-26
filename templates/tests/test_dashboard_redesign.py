import pytest
from models import User, UserReport
from werkzeug.security import generate_password_hash

def test_admin_dashboard_redesign(client, test_db):
    # Create admin
    admin = User(username="admin_dash", password=generate_password_hash("pass"))
    test_db.add(admin)
    test_db.commit()
    
    # Create pending report
    report = UserReport(title="Pending", status="pending", user_id=admin.id)
    test_db.add(report)
    test_db.commit()

    # Login as admin
    with client.session_transaction() as sess:
        sess["admin"] = True

    res = client.get("/admin/")
    assert res.status_code == 200
    html = res.data.decode()
    
    # Check for new elements
    assert "Total Users" in html
    assert "Pending Reports" in html
    assert "Analytics & Charts" in html
    
    # Check that "Recent Alerts" list is GONE (heuristic check)
    # The old template had "Recent Alerts" header
    assert "Recent Alerts" not in html
