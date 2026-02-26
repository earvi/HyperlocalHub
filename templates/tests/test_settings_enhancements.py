import pytest
from models import User, UserPreference, Alert
from werkzeug.security import generate_password_hash, check_password_hash
from app import daily_digest_job
from unittest.mock import patch
from datetime import datetime

def test_save_category_preferences(client, test_db):
    # 1. Setup User
    user = User(username="cat_test", email="cat@test.com", password=generate_password_hash("pass"))
    test_db.add(user)
    test_db.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id

    # 2. Save preference with specific categories
    # Note: Flask's test client handles multiple values for same key as list
    data = {
        "email_digest": "on",
        "categories": ["Traffic", "Weather"]
    }
    client.post("/settings", data=data, follow_redirects=True)

    # 3. Verify DB
    pref = test_db.query(UserPreference).filter_by(user_id=user.id).first()
    assert pref.email_digest is True
    assert "Traffic" in pref.subscribed_categories
    assert "Weather" in pref.subscribed_categories
    assert "University" not in pref.subscribed_categories

@patch("app.db")
@patch("app.send_email")
def test_digest_filtering(mock_send, mock_db, test_db):
    # Mock the DB session for the background job
    mock_db.query.side_effect = test_db.query
    
    # 1. Setup User subscribed ONLY to 'Traffic'
    u = User(username="traffic_fan", email="traffic@test.com", password="x")
    test_db.add(u)
    test_db.commit()
    
    p = UserPreference(user_id=u.id, email_digest=True, subscribed_categories="Traffic")
    test_db.add(p)
    
    # 2. Create Alerts (1 Traffic, 1 Weather)
    a1 = Alert(uid="t1", title="Traffic Jam", category="Traffic", published_at=datetime.utcnow())
    a2 = Alert(uid="w1", title="Sunny Day", category="Weather", published_at=datetime.utcnow())
    test_db.add_all([a1, a2])
    test_db.commit()

    # 3. Run Job
    daily_digest_job()

    daily_digest_job()

    # 4. Verify Email Content
    # Find the call for our user "traffic@test.com"
    found = False
    for args, _ in mock_send.call_args_list:
        recipient, subject, body = args
        if recipient == "traffic@test.com":
            found = True
            assert "Traffic Jam" in body
            assert "Sunny Day" not in body
            
    assert found, "Did not find email sent to traffic@test.com"

def test_change_password(client, test_db):
    u = User(username="pwd_test", email="pwd@test.com", password=generate_password_hash("oldpass"))
    test_db.add(u)
    test_db.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = u.id

    # Change PWM
    client.post("/change-password", data={"new_password": "newpass123"}, follow_redirects=True)

    # Verify
    # Reload user from DB (session might be detadched)
    user = test_db.query(User).get(u.id)
    assert check_password_hash(user.password, "newpass123")

def test_delete_account(client, test_db):
    u = User(username="del_test", email="del@test.com", password="x")
    test_db.add(u)
    test_db.commit()
    pref = UserPreference(user_id=u.id)
    test_db.add(pref)
    test_db.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = u.id

    # Delete
    client.post("/delete-account", follow_redirects=True)

    # Verify gone
    assert test_db.query(User).get(u.id) is None
    assert test_db.query(UserPreference).filter_by(user_id=u.id).first() is None
    
    # Verify logged out
    with client.session_transaction() as sess:
        assert "user_id" not in sess
