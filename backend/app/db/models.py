from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, SmallInteger
from sqlalchemy.dialects.sqlite import BLOB
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .session import Base
import uuid


def gen_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=True)
    timezone = Column(String, nullable=False, default="UTC")
    locale = Column(String, nullable=False, default="en-US")
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

class Task(Base):
    __tablename__ = "tasks"
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String, nullable=False)
    due_at = Column(DateTime, nullable=True, index=True)
    priority = Column(SmallInteger, nullable=False, default=3)
    dynamic_priority = Column(SmallInteger, nullable=True, index=True)
    energy_tag = Column(String, nullable=True)
    status = Column(String, nullable=False, default="Draft", index=True)
    estimated_minutes = Column(Integer, nullable=True)
    version = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

class Calendar(Base):
    __tablename__ = "calendars"
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=True)
    external_provider = Column(String, nullable=True, index=True)
    external_id = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

class Event(Base):
    __tablename__ = "events"
    id = Column(String, primary_key=True, default=gen_uuid)
    calendar_id = Column(String, ForeignKey("calendars.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    start_at = Column(DateTime, nullable=False, index=True)
    end_at = Column(DateTime, nullable=False)
    type = Column(String, nullable=False, default="GENERAL", index=True)
    external_event_id = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
