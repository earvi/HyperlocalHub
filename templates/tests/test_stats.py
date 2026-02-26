import pytest
from models import Alert
from datetime import datetime, timedelta

def test_stats_page(client, test_db):
    # 1. Create dummy alerts
    today = datetime.utcnow()
    a1 = Alert(uid="s1", title="A1", category="University", source="S1", published_at=today)
    a2 = Alert(uid="s2", title="A2", category="Traffic", source="S2", published_at=today - timedelta(days=1))
    a3 = Alert(uid="s3", title="A3", category="University", source="S1", published_at=today - timedelta(days=2))
    
    test_db.add_all([a1, a2, a3])
    test_db.commit()

    # 2. Access Stats Page
    res = client.get("/stats")
    assert res.status_code == 200
    
    # 3. Check for specific data points in HTML (simple string check)
    html = res.data.decode("utf-8")
    assert "University" in html
    assert "Traffic" in html
    assert "S1" in html
    assert "S2" in html
    # Check chart canvas
    # assert 'id="activityChart"' in html
