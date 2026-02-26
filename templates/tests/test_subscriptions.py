import pytest
from models import User, UserPreference
from werkzeug.security import generate_password_hash
from app import daily_digest_job
from unittest.mock import patch

def test_user_subscription_flow(client, test_db):
    # 1. Create a user
    user = User(username="subscriber", email="sub@test.com", password=generate_password_hash("pass"))
    test_db.add(user)
    test_db.commit()

    # 2. Login
    with client.session_transaction() as sess:
        sess["user_id"] = user.id

    # 3. Post to settings to enable digest (Route is /settings, not /user_settings)
    res = client.post("/settings", data={
        "email_digest": "on",
        "alerts_per_page": "10"
    }, follow_redirects=True)
    assert res.status_code == 200

    # 4. Verify DB was updated
    pref = test_db.query(UserPreference).filter_by(user_id=user.id).first()
    assert pref is not None
    assert pref.email_digest is True

@patch("app.db")
@patch("app.send_email")
def test_digest_job_sends_to_subscribers(mock_send, mock_db, test_db):
    # Ensure app.db query method is mocked to return our test_db's query
    mock_db.query.side_effect = test_db.query

    # Setup: 1 subscribed user, 1 unsubscribed
    u1 = User(username="sub", email="yes@test.com", password="x")
    u2 = User(username="unsub", email="no@test.com", password="x")
    test_db.add_all([u1, u2])
    test_db.commit()

    p1 = UserPreference(user_id=u1.id, email_digest=True)
    p2 = UserPreference(user_id=u2.id, email_digest=False)
    test_db.add_all([p1, p2])
    test_db.commit()

    # Need some alerts to trigger sending
    from models import Alert
    from datetime import datetime
    a = Alert(uid="test", title="Test Alert", published_at=datetime.utcnow())
    test_db.add(a)
    test_db.commit()

    daily_digest_job()

    # Verify
    # We can't assert call_count==1 strictly because test_user_subscription_flow might have left a user
    # So we check that our specific subscriber DID get an email, and unsubscribed did NOT.
    calls = [args[0] for args, _ in mock_send.call_args_list]
    assert "yes@test.com" in calls
    assert "no@test.com" not in calls
    # Did not send to "no@test.com"
