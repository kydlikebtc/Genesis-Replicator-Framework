"""Test fixtures for data storage tests."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from genesis_replicator.foundation_services.data_storage.database import Database
from genesis_replicator.foundation_services.data_storage.models import Base

@pytest.fixture
def test_db():
    """Create a test database."""
    database = Database('sqlite:///:memory:')
    database.create_all()
    yield database
    database.drop_all()

@pytest.fixture
def db_session(test_db):
    """Create a test database session."""
    session: Session = test_db.get_session()
    yield session
    session.close()
