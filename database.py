from sqlalchemy.orm import scoped_session, sessionmaker
from models import get_engine, Base

# Create a shared engine and session for the Flask app
engine = get_engine()
session_factory = sessionmaker(bind=engine)
db = scoped_session(session_factory)

def init_db():
    Base.metadata.create_all(engine)
