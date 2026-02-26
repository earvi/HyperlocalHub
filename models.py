
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    create_engine,
    Index,
    Float,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class Admin(Base):
    __tablename__ = "admin"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(128), nullable=False)  # hashed password


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(120), unique=True)
    password = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)
    uid = Column(String(128), unique=True)
    category = Column(String(50))
    source = Column(String(128))
    title = Column(Text, nullable=False)
    summary = Column(Text)
    url = Column(Text)
    # Geo fields
    location = Column(String(256), nullable=True) # Text representation e.g. "Main Gate"
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    
    published_at = Column(DateTime)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    acknowledged = Column(Boolean, default=False)



Index("ix_alerts_published", Alert.published_at)


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True)
    key = Column(String(128), unique=True)
    name = Column(String(256))
    url = Column(Text)
    category = Column(String(50))
    parse_rule = Column(Text)
    last_checked = Column(DateTime)


class Bookmark(Base):
    __tablename__ = "bookmarks"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    alert_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, unique=True)
    default_category = Column(String(50), default="")
    alerts_per_page = Column(Integer, default=10)
    email_digest = Column(Boolean, default=False)
    subscribed_categories = Column(String(256), default="All")
    created_at = Column(DateTime, default=datetime.utcnow)


class SourceHealth(Base):
    __tablename__ = "source_health"

    id = Column(Integer, primary_key=True)
    source_key = Column(String(128), nullable=False)
    status = Column(String(20), nullable=False)   # "OK" / "ERROR"
    message = Column(Text)
    checked_at = Column(DateTime, default=datetime.utcnow)


class UserReport(Base):
    __tablename__ = "user_reports"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(Text, nullable=False)
    description = Column(Text)
    category = Column(String(50))
    # Geo fields
    location = Column(String(256)) # Text description
    lat = Column(Float)
    lon = Column(Float)
    
    status = Column(String(20), default="pending") # pending, approved, rejected

    created_at = Column(DateTime, default=datetime.utcnow)


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships (optional, for convenience)
    # user = relationship("User")
    # alert = relationship("Alert")





class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Optional, can be anon
    endpoint = Column(Text, nullable=False, unique=True)
    p256dh = Column(String(256), nullable=False)
    auth = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)



def get_engine(db_path: str = "sqlite:///hyperlocal.db"):
    return create_engine(db_path, connect_args={"check_same_thread": False})


def get_session(engine):
    Session = sessionmaker(bind=engine)
    return Session()
