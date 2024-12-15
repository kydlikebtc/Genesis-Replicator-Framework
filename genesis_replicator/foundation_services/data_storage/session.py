"""
Database session management and context utilities.
"""
from contextlib import contextmanager
from typing import Generator

from sqlalchemy.orm import Session as SQLAlchemySession

class Session:
    """Session management utilities."""

    def __init__(self, session_factory):
        """Initialize session manager.

        Args:
            session_factory: SQLAlchemy session factory
        """
        self._session_factory = session_factory

    @contextmanager
    def get_session(self) -> Generator[SQLAlchemySession, None, None]:
        """Get a database session with automatic cleanup.

        Yields:
            SQLAlchemy session object
        """
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
