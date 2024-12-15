"""
SQLAlchemy models for the Genesis Replicator Framework.
"""
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import JSON, Column, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped

class Base(DeclarativeBase):
    """Base class for all models."""
    pass

class Agent(Base):
    """Base model for storing agent information."""

    __tablename__ = 'agents'

    id: Mapped[int] = Column(Integer, primary_key=True)
    name: Mapped[str] = Column(String(255), nullable=False)
    type: Mapped[str] = Column(String(50), nullable=False)
    status: Mapped[str] = Column(String(50), nullable=False, default='inactive')
    config: Mapped[Dict[str, Any]] = Column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

class Event(Base):
    """Model for storing system events."""

    __tablename__ = 'events'

    id: Mapped[int] = Column(Integer, primary_key=True)
    type: Mapped[str] = Column(String(50), nullable=False)
    source: Mapped[str] = Column(String(255), nullable=False)
    data: Mapped[Dict[str, Any]] = Column(JSON, nullable=False)
    timestamp: Mapped[datetime] = Column(DateTime, nullable=False, default=datetime.utcnow)

class Transaction(Base):
    """Model for storing blockchain transactions."""

    __tablename__ = 'transactions'

    id: Mapped[int] = Column(Integer, primary_key=True)
    chain_id: Mapped[str] = Column(String(50), nullable=False)
    tx_hash: Mapped[str] = Column(String(66), nullable=False, unique=True)
    status: Mapped[str] = Column(String(50), nullable=False)
    data: Mapped[Dict[str, Any]] = Column(JSON, nullable=False)
    created_at: Mapped[datetime] = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
