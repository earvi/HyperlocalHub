import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, User, Alert
import database
import app

@pytest.fixture(scope="module")
def test_db():
    # Use in-memory SQLite
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Monkeypatch the database session in all modules that imported it
    old_db = database.db
    database.db = session
    
    # We must also patch the references in other modules because they did 'from database import db'
    import auth
    import admin
    import routes.main_routes
    
    auth.db = session
    admin.db = session
    routes.main_routes.db = session
    
    yield session
    
    # Teardown
    session.close()
    Base.metadata.drop_all(engine)
    
    database.db = old_db
    auth.db = old_db
    admin.db = old_db
    routes.main_routes.db = old_db

@pytest.fixture(scope="module")
def client():
    app.app.config["TESTING"] = True
    with app.app.test_client() as client:
        yield client
