from flask import Blueprint, render_template, redirect, url_for, session, request
from sqlalchemy import desc, func
from datetime import datetime

from models import (
    get_engine,
    get_session,
    Base,
    Alert,
    Source,
    SourceHealth,
    UserReport,
    UserReport,
    User,
)
from scraper import scrape

admin = Blueprint("admin", __name__, url_prefix="/admin")

from database import db


def require_admin() -> bool:
    return "admin" in session


def require_user() -> bool:
    return "user_id" in session


@admin.route("/")
def dashboard():
    if not require_admin():
        return redirect(url_for("auth.admin_login"))

    alert_count = db.query(Alert).count()
    source_count = db.query(Source).count()
    pending_count = db.query(UserReport).filter_by(status="pending").count()
    user_count = db.query(User).count()

    return render_template(
        "admin_dashboard.html",
        alert_count=alert_count,
        source_count=source_count,
        pending_count=pending_count,
        user_count=user_count,
    )


@admin.route("/moderation")
def moderation():
    if not require_admin():
        return redirect(url_for("auth.admin_login"))
    
    reports = db.query(UserReport).filter_by(status="pending").order_by(desc(UserReport.created_at)).all()
    return render_template("admin_moderation.html", reports=reports)


@admin.route("/moderation/<int:report_id>/<action>", methods=["POST"])
def moderate_report(report_id, action):
    if not require_admin():
        return redirect(url_for("auth.admin_login"))

    report = db.query(UserReport).get(report_id)
    if not report:
        return redirect(url_for("admin.moderation"))

    if action == "approve":
        report.status = "approved"
        # Convert to Alert
        alert = Alert(
            uid=f"user_report_{report.id}",
            title=report.title,
            summary=report.description,
            category=report.category,
            source="User Report",
            published_at=datetime.utcnow(),
            location=report.location,
            lat=report.lat,
            lon=report.lon,
            url="#" # No external URL
        )
        db.add(alert)
    elif action == "reject":
        report.status = "rejected"
    elif action == "delete":
        db.delete(report)
    
    db.commit()
    return redirect(url_for("admin.moderation"))


@admin.route("/alerts")
def alerts():
    if not require_admin():
        return redirect(url_for("auth.admin_login"))
    # Filter to only show User Reports as requested
    all_alerts = db.query(Alert).filter_by(source="User Report").order_by(desc(Alert.fetched_at)).all()
    return render_template("admin_alerts.html", alerts=all_alerts)


@admin.route("/alerts/<int:alert_id>/delete", methods=["POST"])
def delete_alert(alert_id):
    if not require_admin():
        return redirect(url_for("auth.admin_login"))

    alert = db.query(Alert).get(alert_id)
    if alert:
        db.delete(alert)
        db.commit()

    return redirect(url_for("admin.alerts"))


@admin.route("/sources", methods=["GET", "POST"])
def sources():
    if not require_user():
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        name = request.form["name"]
        url = request.form["url"]
        category = request.form["category"]

        try:
            src = Source(name=name, url=url, key=name, category=category)
            db.add(src)
            db.commit()
            
            # Instant Scrape
            try:
                print(f"Triggering instant scrape for {name}...")
                scrape_target = {
                    "name": name,
                    "url": url,
                    "key": name, 
                    "category": category
                }
                scrape(target_source=scrape_target)
            except Exception as e:
                print(f"Instant scrape failed: {e}")
                
        except Exception as e:
            db.rollback()
            print(f"Error adding source: {e}")
            # In a real app we would flash("Source already exists", "error")
            # For now, just logging and preventing crash.

    all_sources = db.query(Source).all()
    
    from config_sources import PRESET_SOURCES
    return render_template("admin_sources.html", sources=all_sources, presets=PRESET_SOURCES)



@admin.route("/sources/<int:source_id>/delete", methods=["POST"])
def delete_source(source_id):
    if not require_user():
        return redirect(url_for("auth.login"))

    src = db.query(Source).get(source_id)
    if src:
        db.delete(src)
        db.commit()
    
    return redirect(url_for("admin.sources"))








@admin.route("/health")
def health():
    if not require_admin():
        return redirect(url_for("auth.admin_login"))

    subq = (
        db.query(
            SourceHealth.source_key,
            func.max(SourceHealth.checked_at).label("max_checked"),
        )
        .group_by(SourceHealth.source_key)
        .subquery()
    )

    rows = (
        db.query(SourceHealth)
        .join(
            subq,
            (SourceHealth.source_key == subq.c.source_key)
            & (SourceHealth.checked_at == subq.c.max_checked),
        )
        .order_by(SourceHealth.source_key)
        .all()
    )

    return render_template("admin_health.html", rows=rows)
