import sys
from models import get_engine, get_session, Source
from scraper import scrape

engine = get_engine()
db = get_session(engine)

def update_sources():
    sources = db.query(Source).all()
    for s in sources:
        if "MGU University News" in s.name:
            s.url = "https://www.mgu.ac.in/"
            s.key = s.name
            print(f"Updated {s.name}")
        elif "MGU Exam" in s.name:
            s.url = "https://www.mgu.ac.in/orders-notifications-category/exams/"
            s.key = s.name
            print(f"Updated {s.name}")
    
    db.commit()
    print("Database sources updated.")

if __name__ == "__main__":
    update_sources()
    print("Triggering scraper to refresh Health status...")
    scrape()
    print("Done")
