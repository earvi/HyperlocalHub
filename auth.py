from flask import Blueprint, render_template, request, redirect, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from models import (
    get_engine,
    get_session,
    Base,
    Admin,
    User,
    UserPreference,
)

auth = Blueprint("auth", __name__)

from database import db

@auth.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        # Check Admin table first
        admin = db.query(Admin).filter_by(username=username).first()
        if admin and check_password_hash(admin.password, password):
            session.clear()
            session["admin"] = True
            session["admin_username"] = admin.username
            return redirect(url_for("admin.dashboard"))

        # Check User table
        user = db.query(User).filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session.clear()
            session["user_id"] = user.id
            session["username"] = user.username
            return redirect(url_for("main.index"))

        error = "Invalid username or password"
        return render_template("login.html", error=error)

    return render_template("login.html")


@auth.route("/login", methods=["GET", "POST"])
def login():
    return admin_login()


@auth.route("/register", methods=["GET", "POST"])
def register():
    error = None
    message = None

    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form.get("email", "").strip() or None
        password = request.form["password"]
        confirm = request.form["confirm"]

        if password != confirm:
            error = "Passwords do not match."
        elif db.query(User).filter_by(username=username).first():
            error = "Username already taken."
        elif email and db.query(User).filter_by(email=email).first():
            error = "Email already registered."
        else:
            user = User(
                username=username,
                email=email,
                password=generate_password_hash(password),
            )
            db.add(user)
            db.commit()

            pref = UserPreference(
                user_id=user.id, default_category="", alerts_per_page=10
            )
            db.add(pref)
            db.commit()

            message = "Registration successful. You can now log in."

    return render_template("register.html", error=error, message=message)


@auth.route("/register/admin/<token>", methods=["GET", "POST"])
def admin_invite(token):
    # Hardcoded secret for now - in production use env var
    valid_token = "secret-admin-invite-code"
    
    if token != valid_token:
        return "Invalid invite link", 403

    error = None
    message = None

    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        confirm = request.form["confirm"]

        if password != confirm:
            error = "Passwords do not match."
        elif db.query(Admin).filter_by(username=username).first():
            error = "Admin username already taken."
        else:
            admin = Admin(
                username=username,
                password=generate_password_hash(password),
            )
            db.add(admin)
            db.commit()
            message = "Admin registered successfully. Please login."
            return redirect(url_for('auth.admin_login'))

    return render_template("register.html", error=error, message=message, admin_invite=True)


@auth.route("/admin/register", methods=["GET", "POST"])
def admin_register_legacy():
    # Redirect legacy admin register attempt to home or 404
    return redirect(url_for("main.index"))


@auth.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("main.index"))


@auth.route("/logout")
def logout_alias():
    return admin_logout()


@auth.route("/change-password", methods=["POST"])
def change_password():
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    new_password = request.form.get("new_password")
    if new_password:
        user = db.query(User).get(session["user_id"])
        if user:
            user.password = generate_password_hash(new_password)
            db.commit()
    
    return redirect(url_for("main.user_settings"))


@auth.route("/delete-account", methods=["POST"])
def delete_account():
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    
    # Delete User Preferences
    db.query(UserPreference).filter_by(user_id=user_id).delete()
    
    # Delete Bookmarks
    from models import Bookmark
    db.query(Bookmark).filter_by(user_id=user_id).delete()
    
    # Delete User Reports (Optional: or keep them as anonymous? Let's delete for privacy)
    from models import UserReport
    db.query(UserReport).filter_by(user_id=user_id).delete()

    # Delete User
    db.query(User).filter_by(id=user_id).delete()
    db.commit()

    session.clear()
    return redirect(url_for("main.index"))
