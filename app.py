from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

from datetime import datetime, timedelta
from auth import auth
from admin import admin
from routes.main_routes import main_bp
# from routes.feed_routes import feed_bp
from routes.api_routes import api_bp
from database import init_db, db
from scraper import scrape
from models import Alert
from services.email_service import send_email, generate_digest_content
from services.search_service import init_index

from flask_socketio import SocketIO

app = Flask(__name__)
app.secret_key = "supersecretkey-change-me"
app.config['SESSION_TYPE'] = 'filesystem' 

# Initialize SocketIO explicitly with threading for PyInstaller compatibility
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Initialize database
# init_db() 

# Register Blueprints
app.register_blueprint(auth)
app.register_blueprint(admin) 
app.register_blueprint(main_bp)
app.register_blueprint(api_bp)

# Import Socket Events (Must be after socketio init to avoid circular imports if structured poorly, 
# but best to pass socketio instance or use an extension pattern. 
# For this simple app, we can import events here)
from socket_events import register_socket_events
register_socket_events(socketio)


@app.teardown_appcontext
def shutdown_session(exception=None):
    db.remove()

# Scheduler Setup
import os
scheduler = None
if not os.environ.get("TESTING"):
    scheduler = BackgroundScheduler()
    def safe_shutdown():
        try:
            if scheduler.running:
                scheduler.shutdown(wait=False)
        except Exception:
            pass
    atexit.register(safe_shutdown)

def scheduled_job():
    print("Running scheduled scrape...")
    with app.app_context():
        try:
            scrape()
        except Exception as e:
            print(f"Error during scrape: {e}")


def daily_digest_job():
    print("Running daily digest...")
    with app.app_context():
        try:
            # Join User with UserPreference
            from models import User, UserPreference, Alert
            subscribers = (
                db.query(User, UserPreference)
                .join(UserPreference, User.id == UserPreference.user_id)
                .filter(UserPreference.email_digest == True) # noqa
                .all()
            )
            
            print(f"Sending digest to {len(subscribers)} subscribers...")
            
            since = datetime.utcnow() - timedelta(days=1)
            
            for user, pref in subscribers:
                if not user.email:
                    continue

                # Filter alerts for this user
                query = db.query(Alert).filter(Alert.published_at >= since)
                
                # Check categories
                # If "All" or empty, get everything. Otherwise filter IN list
                if pref.subscribed_categories and "All" not in pref.subscribed_categories:
                    cats = pref.subscribed_categories.split(",")
                    query = query.filter(Alert.category.in_(cats))
                
                user_alerts = query.limit(10).all() # Top 10 only
                
                if user_alerts:
                    content = generate_digest_content(user_alerts)
                    send_email(user.email, "Your Custom Daily Digest", content)
                else:
                    print(f"No matching alerts for {user.username}")
                    
        except Exception as e:
            print(f"Error sending digest: {e}")


def cleanup_incidents_job():
    """Auto-delete pending reports older than 24 hours."""
    print("Running incident cleanup...")
    with app.app_context():
        try:
            from models import UserReport
            # Calculate threshold (e.g., 24 hours ago)
            threshold = datetime.utcnow() - timedelta(hours=24)
            
            # Find old pending reports
            deleted_count = db.query(UserReport).filter(
                UserReport.status == "pending",
                UserReport.created_at < threshold
            ).delete()
            
            db.commit()
            if deleted_count > 0:
                print(f"Cleaned up {deleted_count} expired incidents.")
        except Exception as e:
            print(f"Error during incident cleanup: {e}")

if __name__ == "__main__":
    init_db()
    import os
    
    # Only run scheduler/initial tasks in the reloader child process to avoid duplicates
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        init_index() # Initialize Whoosh index
        
        # Schedule tasks
        if scheduler:
            scheduler.add_job(id='scheduled_scrape', func=scheduled_job, trigger="interval", hours=1)
            scheduler.add_job(id='daily_digest', func=daily_digest_job, trigger="interval", hours=24)
            scheduler.add_job(id='cleanup_incidents', func=cleanup_incidents_job, trigger="interval", hours=1) 
            scheduler.start()

    print("Starting Flask server with SocketIO...")
    # Use socketio.run instead of app.run
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, use_reloader=False)
