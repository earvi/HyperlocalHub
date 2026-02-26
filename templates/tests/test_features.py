import os
# Must set before importing app
os.environ["TESTING"] = "1"

import pytest
from app import app
from database import db
from models import Base, Alert, Source, Admin
from sqlalchemy import create_engine
from werkzeug.security import generate_password_hash
from datetime import datetime

@pytest.fixture
def client():
    app.config["TESTING"] = True
    
    # 1. Create In-Memory Engine
    test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    
    # 2. Re-bind the global scoped_session to this new engine
    db.configure(bind=test_engine)
    
    # 3. Create Tables
    Base.metadata.create_all(bind=test_engine)
    
    with app.test_client() as client:
        with app.app_context():
            yield client
            
            # Teardown
            db.remove()
            Base.metadata.drop_all(bind=test_engine)

def test_map_route(client):
    with app.app_context():
        alert = Alert(
            uid="map_test_uid",
            title="Map Test Alert",
            lat=9.6,
            lon=76.5,
            location="Test Loc",
            published_at=datetime.utcnow()
        )
        db.add(alert)
        db.commit()

    res = client.get("/map")
    assert res.status_code == 200
    assert b"Map Test Alert" in res.data

def test_api_alerts_no_key(client):
    res = client.get("/api/v1/alerts")
    assert res.status_code == 401

def test_api_alerts_with_key(client):
    from routes.api_routes import API_KEYS
    key = list(API_KEYS.keys())[0] 
    
    res = client.get("/api/v1/alerts", headers={"X-API-Key": key})
    assert res.status_code == 200
    assert isinstance(res.json, list)

def test_delete_source(client):
    src_id = None
    with app.app_context():
        admin = Admin(username="admin_del", password=generate_password_hash("pass"))
        db.add(admin)
        
        src = Source(name="To Delete", url="http://delete.me", key="del_me", category="Test")
        db.add(src)
        db.commit()
        src_id = src.id

    with client.session_transaction() as sess:
        sess["admin"] = True
        sess["user_id"] = 999 
        sess["admin_username"] = "admin_del"

    res = client.post(f"/admin/sources/{src_id}/delete", follow_redirects=True)
    assert res.status_code == 200
    
    with app.app_context():
        deleted = db.query(Source).get(src_id)
        assert deleted is None
