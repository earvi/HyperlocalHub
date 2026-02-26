import pytest
from models import User, Source
from sqlalchemy.exc import IntegrityError

def test_add_duplicate_source_handled_gracefully(client, test_db):
    # 1. Setup User
    u = User(username="admin_dup", email="dup@test.com", password="x")
    test_db.add(u)
    test_db.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = u.id

    # 2. Add Source first time
    s1 = Source(name="Dup Source", url="http://dup.com", key="Dup Source", category="Tech")
    test_db.add(s1)
    test_db.commit()

    # 3. Add same source again via POST
    data = {
        "name": "Dup Source", # Same name = Same Key
        "url": "http://dup.com",
        "category": "Tech"
    }
    
    # This should NOT crash with 500 or PendingRollbackError
    # It should catch exception and redirect (or render template)
    res = client.post("/admin/sources", data=data, follow_redirects=True)
    
    assert res.status_code == 200
    # Ensure app is still alive
    assert b"Source" in res.data
    
    # Ensure only 1 source exists
    count = test_db.query(Source).filter_by(key="Dup Source").count()
    assert count == 1
