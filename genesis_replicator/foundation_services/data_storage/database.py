"""
Database connection and configuration management.
"""
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from .models import Base

class Database:
    """Main database interface for the Genesis Replicator Framework."""

    def __init__(self, connection_url: str):
        """Initialize database connection.

        Args:
            connection_url: SQLAlchemy connection URL
        """
        self._engine: Engine = create_engine(
            connection_url,
            pool_pre_ping=True,  # Enable connection health checks
            pool_size=5,         # Default connection pool size
            max_overflow=10      # Maximum number of connections
        )
        self._session_factory = sessionmaker(bind=self._engine)

    def create_all(self) -> None:
        """Create all database tables."""
        Base.metadata.create_all(self._engine)

    def drop_all(self) -> None:
        """Drop all database tables."""
        Base.metadata.drop_all(self._engine)

    def get_session(self):
        """Get a new database session."""
        return self._session_factory()

    @property
    def engine(self) -> Engine:
        """Get the SQLAlchemy engine instance."""
        return self._engine
