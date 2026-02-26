from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from datetime import datetime, timedelta
from sqlalchemy import desc, or_, func
from database import db
from models import Alert, Bookmark, UserPreference, UserReport, Comment


main_bp = Blueprint('main', __name__)

@main_bp.route("/report", methods=["GET", "POST"])
def report_incident():
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        category = request.form["category"]
        location = request.form["location"]
        lat = request.form["lat"]
        lon = request.form["lon"]

        try:
            report = UserReport(
                user_id=session["user_id"],
                title=title,
                description=description,
                category=category,
                location=location,
                lat=float(lat),
                lon=float(lon)
            )
            db.add(report)
            db.commit()
            # flash("Report submitted! It will appear after moderation.", "success")
            return redirect(url_for("main.index"))
        except ValueError:
            # flash("Invalid location data.", "error")
            return "Invalid coordinate data", 400

    return render_template("report.html")



@main_bp.route("/")
def index():
    q = request.args.get("q", "")
    category = request.args.get("category")
    page = int(request.args.get("page", 1))

    per_page = 10

    if session.get("user_id"):
        pref = (
            db.query(UserPreference)
            .filter_by(user_id=session["user_id"])
            .first()
        )
        if pref:
            if category is None or category == "":
                category = pref.default_category or ""
            per_page = pref.alerts_per_page or 10

    if category is None:
        category = ""

    filter_type = request.args.get("filter")

    query = db.query(Alert)

    # User Filters (Login Required)
    if filter_type in ['starred', 'liked'] and session.get("user_id"):
        if filter_type == 'starred':
            query = query.join(Bookmark, Alert.id == Bookmark.alert_id).filter(Bookmark.user_id == session["user_id"])

    
    if q:
        query = query.filter(
            or_(Alert.title.ilike(f"%{q}%"), Alert.summary.ilike(f"%{q}%"))
        )

    if category:
        query = query.filter(Alert.category == category)

    # Geolocation Filter
    user_lat = request.args.get("lat", type=float)
    user_lon = request.args.get("lon", type=float)
    
    # If geolocation is active, we need to fetch candidates and filter in Python
    # (SQLite doesn't do complex math easily)
    if user_lat and user_lon:
        # Fetch more candidates to filter
        query = query.filter(Alert.lat.isnot(None), Alert.lon.isnot(None))
        # We can't limit yet because we need to sort by distance first
        all_candidates = query.all()
        
        filtered_alerts = []
        for a in all_candidates:
             try:
                 d = haversine(user_lat, user_lon, float(a.lat), float(a.lon))
                 if d <= 10.0: # 10km Radius
                     a.distance = round(d, 1)
                     filtered_alerts.append(a)
             except (ValueError, TypeError):
                 continue
        
        # Sort by distance
        filtered_alerts.sort(key=lambda x: x.distance)
        
        total = len(filtered_alerts)
        total_pages = (total + per_page - 1) // per_page
        
        # Pagination in Python
        start = (page - 1) * per_page
        end = start + per_page
        alerts = filtered_alerts[start:end]
        
    else:
        # Standard DB-side pagination
        total = query.count()
        alerts = (
            query.order_by(desc(Alert.fetched_at))
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        total_pages = (total + per_page - 1) // per_page


    # Attach stats (N+1 query for simplicity in this prototype, or optimize with efficient joins later)
    for a in alerts:
        a.comment_count = db.query(Comment).filter_by(alert_id=a.id).count()

    bookmarked_ids = set()
    if session.get("user_id"):
        rows = (
            db.query(Bookmark.alert_id)
            .filter(Bookmark.user_id == session["user_id"])
            .all()
        )
        bookmarked_ids = {r.alert_id for r in rows}

    return render_template(
        "index.html",
        alerts=alerts,
        page=page,
        total_pages=total_pages,
        q=q,
        category=category,
        filter_type=filter_type,
        bookmarked_ids=bookmarked_ids,
        per_page=per_page,
        user_lat=user_lat,
        user_lon=user_lon
    )

def haversine(lat1, lon1, lat2, lon2):
    import math
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) * math.sin(dlat / 2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) * math.sin(dlon / 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


@main_bp.route("/map")
def map_view():
    # Fetch verified alerts
    alerts = db.query(Alert).filter(Alert.lat.isnot(None)).limit(100).all()
    
    # Fetch pending user reports
    reports = db.query(UserReport).filter(
        UserReport.lat.isnot(None), 
        UserReport.status == 'pending'
    ).limit(50).all()

    alerts_data = []

    # Add Verified Alerts
    for a in alerts:
        alerts_data.append({
            "id": a.id,
            "title": a.title,
            "lat": a.lat,
            "lon": a.lon,
            "category": a.category,
            "summary": a.summary,
            "url": a.url,
            "verified": True
        })

    # Add Pending Reports
    for r in reports:
        # Note: Reports don't support chat yet strictly speaking, preventing ID overlap issues
        # But for map rendering we need unique IDs. 
        # Using a negative ID or string ID might break int() casting in JS.
        # For now, let's just pass raw ID but logic might need update if we want chat for reports.
        alerts_data.append({
            "id": r.id, 
            "title": f"[Report] {r.title}",
            "lat": r.lat,
            "lon": r.lon,
            "category": r.category,
            "summary": r.description,
            "url": "#", 
            "verified": False,
            "is_report": True
        })

    return render_template("map.html", alerts=alerts_data, title="Alert Map")


@main_bp.route("/sw.js")
def service_worker():
    from flask import send_from_directory, current_app
    return send_from_directory(current_app.static_folder, 'sw.js')



@main_bp.route("/settings", methods=["GET", "POST"])
def user_settings():
    if not session.get("user_id"):
        return redirect(url_for("auth.admin_login"))

    pref = (
        db.query(UserPreference)
        .filter_by(user_id=session["user_id"])
        .first()
    )

    if request.method == "POST":
        default_category = request.form.get("default_category", "")
        try:
            alerts_per_page = int(request.form.get("alerts_per_page", 10))
        except ValueError:
            alerts_per_page = 10
            
        email_digest = True if request.form.get("email_digest") else False
        
        # Get list of selected categories
        categories = request.form.getlist("categories")
        subscribed_cats = ",".join(categories) if categories else "All"

        if not pref:
            pref = UserPreference(
                user_id=session["user_id"],
                default_category=default_category,
                alerts_per_page=alerts_per_page,
                email_digest=email_digest,
                subscribed_categories=subscribed_cats
            )
            db.add(pref)
        else:
            pref.default_category = default_category
            pref.alerts_per_page = alerts_per_page
            pref.email_digest = email_digest
            pref.subscribed_categories = subscribed_cats
        
        db.commit()
        # Update session for immediate effect if needed (not needed for these prefs)
        return redirect(url_for("main.user_settings"))

    my_reports = (
        db.query(UserReport)
        .filter_by(user_id=session["user_id"])
        .order_by(desc(UserReport.created_at))
        .all()
    )

    return render_template("user_settings.html", pref=pref, my_reports=my_reports)


@main_bp.route("/bookmark/<int:alert_id>", methods=["POST"])
def bookmark(alert_id):
    if not session.get("user_id"):
        return jsonify({"ok": False, "error": "login_required"}), 401

    existing = (
        db.query(Bookmark)
        .filter_by(user_id=session["user_id"], alert_id=alert_id)
        .first()
    )
    if existing:
        return jsonify({"ok": True, "status": "already"})

    bm = Bookmark(user_id=session["user_id"], alert_id=alert_id)
    db.add(bm)
    db.commit()
    return jsonify({"ok": True, "status": "added"})


@main_bp.route("/bookmark/<int:alert_id>/remove", methods=["POST"])
def remove_bookmark(alert_id):
    if not session.get("user_id"):
        return jsonify({"ok": False, "error": "login_required"}), 401

    db.query(Bookmark).filter_by(
        user_id=session["user_id"], alert_id=alert_id
    ).delete()
    db.commit()
    return jsonify({"ok": True, "status": "removed"})





@main_bp.route("/alert/<int:alert_id>/comment", methods=["POST"])
def comment_alert(alert_id):
    if not session.get("user_id"):
        return jsonify({"ok": False, "error": "login_required"}), 401
    
    text = request.json.get("text")
    if not text:
        return jsonify({"ok": False, "error": "empty_text"}), 400

    c = Comment(user_id=session["user_id"], alert_id=alert_id, text=text)
    db.add(c)
    db.commit()

    # Real-time Broadcast
    try:
        from app import socketio
        user_name = session.get("username", "Someone")
        socketio.emit('new_comment', {
            "alert_id": alert_id,
            "user": user_name,
            "text": text,
            "created_at": "Just now",
            "is_owner": False # Receiver is not owner
        }, room=f"alert_{alert_id}")
    except Exception as e:
        print(f"Socket emit failed: {e}")

    return jsonify({
        "ok": True, 
        "comment": {
            "user": session.get("username", "You"), # Ideally fetch from DB
            "text": text,
            "created_at": "Just now"
        }
    })


@main_bp.route("/alert/<int:alert_id>/comments", methods=["GET"])
def get_comments(alert_id):
    # Join with User to get usernames
    from models import User, Bookmark
    comments = (
        db.query(Comment, User.username)
        .join(User, Comment.user_id == User.id)
        .filter(Comment.alert_id == alert_id)
        .order_by(Comment.created_at.asc())
        .all()
    )
    
    data = [{
        "id": c.id,
        "user": username,
        "text": c.text,
        "created_at": c.created_at.strftime("%Y-%m-%d %H:%M"),
        "is_owner": (session.get("user_id") == c.user_id) or session.get("admin")
    } for c, username in comments]
    
    return jsonify({"ok": True, "comments": data})


@main_bp.route("/report/<int:report_id>/delete", methods=["POST"])
def delete_own_report(report_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    
    report = db.query(UserReport).get(report_id)
    
    if report:
        if int(report.user_id) == int(session["user_id"]):
            try:
                # 1. Check if there is an associated Alert (if it was approved)
                associated_alert_uid = f"user_report_{report.id}"
                alert = db.query(Alert).filter_by(uid=associated_alert_uid).first()
                if alert:
                    db.delete(alert)
                    # flush to ensure alert is gone before report
                    db.flush() 

                # 2. Delete the Report
                db.delete(report)
                db.commit()
                # flash("Report deleted successfully.", "success")
            except Exception as e:
                db.rollback()
                print(f"Error deleting report: {e}")
                # flash("Error deleting report.", "error")
        else:
             pass # Ownership mismatch
    
    return redirect(url_for("main.user_settings"))


@main_bp.route("/comment/<int:comment_id>/delete", methods=["POST"])
def delete_comment(comment_id):
    if not session.get("user_id"):
        return jsonify({"ok": False, "error": "login_required"}), 401

    comment = db.query(Comment).get(comment_id)
    if not comment:
        return jsonify({"ok": False, "error": "not_found"}), 404

    # Allow Delete if Owner OR Admin
    if comment.user_id != session["user_id"] and not session.get("admin"):
        return jsonify({"ok": False, "error": "forbidden"}), 403

    db.delete(comment)
    db.commit()

    return jsonify({"ok": True})


def alert_to_dict(a: Alert):
    return {
        "id": a.id,
        "uid": a.uid,
        "title": a.title,
        "summary": a.summary,
        "url": a.url,
        "category": a.category,
        "source": a.source,
        "published_at": a.published_at.isoformat() if a.published_at else None,
        "fetched_at": a.fetched_at.isoformat() if a.fetched_at else None,
    }


@main_bp.route("/api/alerts")
def api_alerts():
    q = request.args.get("q", "")
    category = request.args.get("category", "")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))

    query = db.query(Alert)

    if q:
        query = query.filter(
            or_(Alert.title.ilike(f"%{q}%"), Alert.summary.ilike(f"%{q}%"))
        )

    if category:
        query = query.filter(Alert.category == category)

    total = query.count()
    alerts = (
        query.order_by(desc(Alert.fetched_at))
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return jsonify(
        {
            "page": page,
            "per_page": per_page,
            "total": total,
            "results": [alert_to_dict(a) for a in alerts],
        }
    )


@main_bp.route("/api/alerts/<int:alert_id>")
def api_alert_detail(alert_id):
    a = db.query(Alert).get(alert_id)
    if not a:
        return jsonify({"error": "not_found"}), 404
    return jsonify(alert_to_dict(a))


@main_bp.route("/stats")
def stats():
    from models import User
    # 1. Alerts Trend (Last 7 Days) - REPLACES Category Chart
    # Calculate last 7 days dates
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=6)
    
    # Initialize dictionary with 0 for all 7 days
    alerts_map = {}
    for i in range(7):
        d = start_date + timedelta(days=i)
        alerts_map[d] = 0
        
    # Query DB for this range
    alert_rows = (
        db.query(func.date(Alert.published_at), func.count(Alert.id))
        .filter(func.date(Alert.published_at) >= start_date)
        .group_by(func.date(Alert.published_at))
        .all()
    )
    
    # Update map
    for date_obj, count in alert_rows:
        if isinstance(date_obj, str):
            d_key = datetime.strptime(date_obj, '%Y-%m-%d').date()
        else:
            d_key = date_obj
        if d_key in alerts_map:
            alerts_map[d_key] = count
            
    sorted_dates = sorted(alerts_map.keys())
    trend_dates = [d.strftime('%Y-%m-%d') for d in sorted_dates]
    trend_counts = [alerts_map[d] for d in sorted_dates]

    # 3. Top Sources
    src_rows = (
        db.query(Alert.source, func.count(Alert.id))
        .group_by(Alert.source)
        .order_by(desc(func.count(Alert.id)))
        .limit(5)
        .all()
    )
    src_labels = [r[0] or "Unknown" for r in src_rows]
    src_values = [r[1] for r in src_rows]

    # 4. User Growth (Last 7 Days) - Admin Only
    user_dates = []
    user_counts = []
    
    if session.get("admin"):
        # Initialize dictionary with 0 for all 7 days
        users_map = {}
        for i in range(7):
            d = start_date + timedelta(days=i)
            users_map[d] = 0
            
        user_rows = (
            db.query(func.date(User.created_at), func.count(User.id))
            .filter(func.date(User.created_at) >= start_date)
            .group_by(func.date(User.created_at))
            .all()
        )
        
        for date_obj, count in user_rows:
            if isinstance(date_obj, str):
                d_key = datetime.strptime(date_obj, '%Y-%m-%d').date()
            else:
                d_key = date_obj
            if d_key in users_map:
                users_map[d_key] = count
                
        sorted_user_dates = sorted(users_map.keys())
        user_dates = [d.strftime('%Y-%m-%d') for d in sorted_user_dates]
        user_counts = [users_map[d] for d in sorted_user_dates]

    return render_template(
        "stats.html",
        trend_dates=trend_dates,
        trend_counts=trend_counts,
        src_labels=src_labels,
        src_values=src_values,
        user_dates=user_dates,
        user_counts=user_counts,
        is_admin=session.get("admin")
    )
