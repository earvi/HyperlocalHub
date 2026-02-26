import pytest
from models import UserReport, Alert, Admin, User
from werkzeug.security import generate_password_hash

def test_user_report_submission(client, test_db):
    # Create user
    user = User(username="reporter", password=generate_password_hash("pass"))
    test_db.add(user)
    test_db.commit()
    
    # Login
    with client.session_transaction() as sess:
        sess["user_id"] = user.id

    # Submit report
    res = client.post("/report", data={
        "title": "Test Accident",
        "description": "A bad crash",
        "category": "Traffic",
        "location": "Main Road",
        "lat": "9.6",
        "lon": "76.5"
    }, follow_redirects=True)
    
    assert res.status_code == 200
    
    # Check DB
    report = test_db.query(UserReport).first()
    assert report is not None
    assert report.title == "Test Accident"
    assert report.status == "pending"

def test_admin_moderation_approval(client, test_db):
    # Create admin
    admin = Admin(username="admin_mod", password=generate_password_hash("pass"))
    test_db.add(admin)
    
    # Create pending report
    report = UserReport(
        user_id=1,
        title="Pending Report",
        description="Verify me",
        category="Safety",
        location="Somewhere",
        lat=10.0,
        lon=76.0,
        status="pending"
    )
    test_db.add(report)
    test_db.commit()
    report_id = report.id

    # Login as admin
    with client.session_transaction() as sess:
        sess["admin"] = True

    # Approve
    res = client.post(f"/admin/moderation/{report_id}/approve", follow_redirects=True)
    assert res.status_code == 200
    
    # Verify status changed
    updated_report = test_db.query(UserReport).get(report_id)
    assert updated_report.status == "approved"
    
    # Verify Alert created
    alert = test_db.query(Alert).filter_by(title="Pending Report").first()
    assert alert is not None
    assert alert.category == "Safety"
    assert alert.source == "User Report"

def test_admin_moderation_rejection(client, test_db):
    # Create admin
    admin = Admin(username="admin_mod2", password=generate_password_hash("pass"))
    test_db.add(admin)
    
    # Create pending report
    report = UserReport(title="Bad Report", status="pending")
    test_db.add(report)
    test_db.commit()
    
    # Login as admin
    with client.session_transaction() as sess:
        sess["admin"] = True

    # Reject
    client.post(f"/admin/moderation/{report.id}/reject", follow_redirects=True)
    
    # Verify status
    updated_report = test_db.query(UserReport).get(report.id)
    assert updated_report.status == "rejected"
    
    # Verify NO Alert created
    alert = test_db.query(Alert).filter_by(title="Bad Report").first()
    assert alert is None
