import pytest
from unittest.mock import patch, MagicMock
from models import User

@patch("admin.scrape")
def test_add_source_triggers_scrape(mock_scrape, client, test_db):
    # 1. Setup User (requires user login to manage sources)
    u = User(username="admin_scrape", email="scrape@test.com", password="x")
    test_db.add(u)
    test_db.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = u.id

    # 2. Add a Source
    data = {
        "name": "Instant News",
        "url": "http://instant.news",
        "category": "General"
    }
    
    # We need to mock the DB add/commit implicitly handled by app code via `database.db` 
    # but since our test setup patches database.db, it should work fine.
    
    res = client.post("/admin/sources", data=data, follow_redirects=True)
    assert res.status_code == 200

    # 3. Verify Scrape was called
    assert mock_scrape.called
    args, kwargs = mock_scrape.call_args
    
    # Check arguments
    target = kwargs.get('target_source')
    assert target is not None
    assert target["name"] == "Instant News"
    assert target["url"] == "http://instant.news"
    assert target["category"] == "General"
