from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, SmallInteger, JSON
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
    # Calendar attributes
    time_zone = Column(String, nullable=True)
    access_role = Column(String, nullable=True)
    color = Column(String, nullable=True)
    is_primary = Column(Integer, nullable=False, default=0, index=True)  # 0/1 as boolean
    is_default = Column(Integer, nullable=False, default=0, index=True)  # user-chosen default calendar
    selected = Column(Integer, nullable=False, default=1, index=True)    # participate in scheduling
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

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


class IntegrationAccount(Base):
    __tablename__ = "integration_accounts"
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String, nullable=False, index=True)  # e.g. 'google'
    scopes = Column(JSON, nullable=True)  # list of scopes (stored as JSON array in SQLite)
    access_token_hash = Column(String, nullable=False)
    refresh_token_hash = Column(String, nullable=True)
    # 新方式: 暗号化保存（移行期間は hash と併存）
    access_token_encrypted = Column(String, nullable=True)
    refresh_token_encrypted = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    sync_token = Column(String, nullable=True)
    revoked_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

