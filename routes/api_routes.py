from flask import Blueprint, request, jsonify, g
from functools import wraps
from database import db
from models import Alert
from services.search_service import search_alerts

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

# Hardcoded for demo - in prod use DB table
API_KEYS = {
    "demo-key-123": "Developer"
}

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        key = request.headers.get('X-API-Key')
        if not key or key not in API_KEYS:
            return jsonify({"error": "Unauthorized. Invalid or missing API Key."}), 401
        return f(*args, **kwargs)
    return decorated_function

@api_bp.route("/alerts", methods=["GET"])
@require_api_key
def get_alerts():
    limit = request.args.get("limit", 20, type=int)
    category = request.args.get("category")
    
    query = db.query(Alert)
    if category:
        query = query.filter(Alert.category == category)
    
    alerts = query.order_by(Alert.published_at.desc()).limit(limit).all()
    
    return jsonify([
        {
            "id": a.id,
            "title": a.title,
            "summary": a.summary,
            "url": a.url,
            "category": a.category,
            "published_at": a.published_at.isoformat() if a.published_at else None
        } for a in alerts
    ])

@api_bp.route("/search", methods=["GET"])
@require_api_key
def search():
    q = request.args.get("q")
    if not q:
        return jsonify({"error": "Missing query parameter 'q'"}), 400
        
    results = search_alerts(q)
    return jsonify({"count": len(results), "results": results})


@api_bp.route("/subscribe", methods=["POST"])
def subscribe():
    """Save a push subscription."""
    data = request.json
    if not data or not data.get("endpoint"):
        return jsonify({"error": "Invalid data"}), 400

    from models import PushSubscription
    
    # Check if exists
    existing = db.query(PushSubscription).filter_by(endpoint=data["endpoint"]).first()
    if existing:
        # Update user_id if changed
        if session.get("user_id"):
            existing.user_id = session["user_id"]
            db.commit()
        return jsonify({"status": "updated"})

    # Create new
    sub = PushSubscription(
        user_id=session.get("user_id"),
        endpoint=data["endpoint"],
        p256dh=data["keys"]["p256dh"],
        auth=data["keys"]["auth"]
    )
    db.add(sub)
    db.commit()
    return jsonify({"status": "created"})


@api_bp.route("/trigger_push", methods=["POST"])
@require_api_key
def trigger_push():
    """Manually trigger a push notification (Admin/Dev)."""
    data = request.json
    message = data.get("message", "Hello World!")
    url = data.get("url", "/")
    
    from services.push_service import send_push_to_all
    count = send_push_to_all(message, url)
    
    return jsonify({"status": "sent", "count": count})
