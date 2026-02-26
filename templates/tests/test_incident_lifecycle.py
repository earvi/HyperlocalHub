import os
# Must set before importing app
os.environ["TESTING"] = "1"

import pytest
from app import app
from database import db
from models import Base, User, UserReport, Alert
from sqlalchemy import create_engine
from werkzeug.security import generate_password_hash
import json

@pytest.fixture
def client():
    app.config["TESTING"] = True
    test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    db.configure(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    
    with app.test_client() as client:
        with app.app_context():
            yield client
            db.remove()
            Base.metadata.drop_all(bind=test_engine)

def test_incident_lifecycle(client):
    # 1. Register User
    user_id = None
    with app.app_context():
        u = User(username="reporter", email="rep@test.com", password=generate_password_hash("pass"))
        db.add(u)
        db.commit()
        user_id = u.id

    # 2. Login
    with client.session_transaction() as sess:
        sess["user_id"] = user_id

    # 3. Create Report
    res = client.post("/report", data={
        "title": "Pothole",
        "description": "Big hole",
        "category": "Traffic",
        "location": "Main St",
        "lat": "10.0",
        "lon": "76.0"
    }, follow_redirects=True)
    assert res.status_code == 200
    
    report_id = None
    with app.app_context():
        report = db.query(UserReport).filter_by(title="Pothole").first()
        assert report is not None
        assert report.status == "pending"
        report_id = report.id

    # 4. Admin Login
    # Create Admin user just in case auth checks DB
    with app.app_context():
        a = User(username="admin_guy", email="admin@test.com", password=generate_password_hash("pass")) 
        db.add(a)
        db.commit()

    with client.session_transaction() as sess:
        sess["admin"] = True
        sess["admin_username"] = "admin_guy"

    # 5. Approve Report
    res = client.post(f"/admin/moderation/{report_id}/approve", follow_redirects=True)
    assert res.status_code == 200

    # 6. Verify Alert Created
    with app.app_context():
        # Check Report Status
        updated_report = db.query(UserReport).get(report_id)
        assert updated_report.status == "approved"
        
        # Check Alert
        alert = db.query(Alert).filter(Alert.uid == f"user_report_{report_id}").first()
        assert alert is not None
        assert alert.title == "Pothole"
