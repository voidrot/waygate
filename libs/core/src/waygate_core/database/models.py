"""Canonical SQLAlchemy declarative metadata roots for WayGate."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base declarative model for first-party WayGate ORM tables."""
