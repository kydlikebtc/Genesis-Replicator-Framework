"""Test cases for database management."""
import pytest
from sqlalchemy.orm import Session

from genesis_replicator.foundation_services.data_storage.database import Database
from genesis_replicator.foundation_services.data_storage.models import Agent

def test_database_connection():
    """Test database connection and initialization."""
    db = Database('sqlite:///:memory:')
    db.create_all()
    assert db.engine is not None

def test_session_management(test_db):
    """Test session creation and management."""
    session = test_db.get_session()
    assert isinstance(session, Session)
    session.close()

def test_database_operations(test_db):
    """Test basic database operations."""
    session = test_db.get_session()

    # Create
    agent = Agent(name='test', type='test', status='active', config={})
    session.add(agent)
    session.commit()

    # Read
    saved_agent = session.query(Agent).first()
    assert saved_agent.name == 'test'

    # Update
    saved_agent.status = 'inactive'
    session.commit()
    updated_agent = session.query(Agent).first()
    assert updated_agent.status == 'inactive'

    # Delete
    session.delete(saved_agent)
    session.commit()
    assert session.query(Agent).first() is None

    session.close()
