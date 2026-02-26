from models import User, Alert
from datetime import datetime

def test_user_creation(test_db):
    user = User(username="testuser", email="test@example.com", password="hashedpassword")
    test_db.add(user)
    test_db.commit()

    saved_user = test_db.query(User).filter_by(username="testuser").first()
    assert saved_user is not None
    assert saved_user.email == "test@example.com"

def test_alert_creation(test_db):
    alert = Alert(
        uid="123",
        title="Test Alert",
        summary="This is a test summary",
        published_at=datetime.utcnow()
    )
    test_db.add(alert)
    test_db.commit()

    saved = test_db.query(Alert).filter_by(uid="123").first()
    assert saved is not None
    assert saved.title == "Test Alert"
