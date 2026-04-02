from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    avatar_url = Column(String, nullable=True)
    password_hash = Column(String, nullable=True)
    auth_provider = Column(String, nullable=False, default="local")
    created_at = Column(DateTime(timezone=True), default=_now)

    roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")


class Role(Base):
    __tablename__ = "roles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, nullable=False)

    users = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")


class UserRole(Base):
    __tablename__ = "user_roles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    role_id = Column(String, ForeignKey("roles.id"), nullable=False)

    user = relationship("User", back_populates="roles")
    role = relationship("Role", back_populates="users")


class DistrictSetting(Base):
    __tablename__ = "district_settings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    district_id = Column(String, unique=True, nullable=False, index=True)
    default_params = Column(JSON, nullable=True)
    benchmark_overrides = Column(JSON, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)
    updated_by = Column(String, ForeignKey("users.id"), nullable=True)


class DistrictNote(Base):
    __tablename__ = "district_notes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    district_id = Column(String, nullable=False, index=True)
    note = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)


class DistrictTarget(Base):
    __tablename__ = "district_targets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    district_id = Column(String, unique=True, nullable=False, index=True)
    targets = Column(JSON, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)
    updated_by = Column(String, ForeignKey("users.id"), nullable=True)


class Run(Base):
    __tablename__ = "runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    district_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=_now, index=True)
    status = Column(String, default="pending", index=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    approved_by = Column(String, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    summary = Column(JSON, nullable=False)
    full_result = Column(JSON, nullable=False)


class Preset(Base):
    __tablename__ = "presets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    config = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    district_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(String, nullable=False)
    metric = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)
    is_active = Column(Boolean, default=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    action = Column(String, nullable=False)
    actor_id = Column(String, ForeignKey("users.id"), nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, index=True)


class ActivityEvent(Base):
    __tablename__ = "activity_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    actor_id = Column(String, ForeignKey("users.id"), nullable=True)
    district_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, index=True)


class AIChatMessage(Base):
    __tablename__ = "ai_chat_messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    district_id = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
