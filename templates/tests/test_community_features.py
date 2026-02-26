import pytest
from models import User, Alert, Comment

def test_comments(client, test_db):
    # Setup User & Alert
    u = User(username="comm_tester", email="comm@test.com", password="x")
    a = Alert(uid="comm_alert", title="Comm Alert", summary="Test", url="http://x.com")
    test_db.add(u)
    test_db.add(a)
    test_db.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = u.id



    # 3. Comment
    res = client.post(f"/alert/{a.id}/comment", json={"text": "Hello World"})
    assert res.json["ok"] is True
    assert res.json["comment"]["text"] == "Hello World"

    # 4. Get Comments
    res = client.get(f"/alert/{a.id}/comments")
    assert res.json["ok"] is True
    assert len(res.json["comments"]) == 1
    assert res.json["comments"][0]["text"] == "Hello World"
