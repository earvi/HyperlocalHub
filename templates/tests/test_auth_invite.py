from models import Admin, User

def test_admin_invite_route(client, test_db):
    # Invalid Token
    res = client.get("/register/admin/wrong-token")
    assert res.status_code == 403

    # Valid Token
    res = client.get("/register/admin/secret-admin-invite-code")
    assert res.status_code == 200
    assert b"Admin Registration" in res.data

def test_user_registration_default(client, test_db):
    # Public register should create USER not ADMIN
    res = client.post("/register", data={
        "username": "publicuser",
        "password": "password",
        "confirm": "password"
    }, follow_redirects=True)
    
    assert res.status_code == 200
    
    user = test_db.query(User).filter_by(username="publicuser").first()
    admin = test_db.query(Admin).filter_by(username="publicuser").first()
    
    assert user is not None
    assert admin is None
