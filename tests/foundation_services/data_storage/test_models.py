"""Test cases for data storage models."""
from datetime import datetime

import pytest

from genesis_replicator.foundation_services.data_storage.models import Agent, Event, Transaction

def test_create_agent(db_session):
    """Test creating and retrieving an agent."""
    agent = Agent(
        name='test_agent',
        type='trading',
        status='active',
        config={'key': 'value'}
    )
    db_session.add(agent)
    db_session.commit()

    saved_agent = db_session.query(Agent).first()
    assert saved_agent.name == 'test_agent'
    assert saved_agent.type == 'trading'
    assert saved_agent.status == 'active'
    assert saved_agent.config == {'key': 'value'}
    assert isinstance(saved_agent.created_at, datetime)
    assert isinstance(saved_agent.updated_at, datetime)

def test_create_event(db_session):
    """Test creating and retrieving an event."""
    event = Event(
        type='blockchain_event',
        source='ethereum',
        data={'block': 123, 'event': 'Transfer'}
    )
    db_session.add(event)
    db_session.commit()

    saved_event = db_session.query(Event).first()
    assert saved_event.type == 'blockchain_event'
    assert saved_event.source == 'ethereum'
    assert saved_event.data == {'block': 123, 'event': 'Transfer'}
    assert isinstance(saved_event.timestamp, datetime)

def test_create_transaction(db_session):
    """Test creating and retrieving a transaction."""
    tx = Transaction(
        chain_id='1',
        tx_hash='0x123...abc',
        status='pending',
        data={'gas': 21000, 'value': '1.0'}
    )
    db_session.add(tx)
    db_session.commit()

    saved_tx = db_session.query(Transaction).first()
    assert saved_tx.chain_id == '1'
    assert saved_tx.tx_hash == '0x123...abc'
    assert saved_tx.status == 'pending'
    assert saved_tx.data == {'gas': 21000, 'value': '1.0'}
    assert isinstance(saved_tx.created_at, datetime)
    assert isinstance(saved_tx.updated_at, datetime)

def test_unique_tx_hash_constraint(db_session):
    """Test that transaction hash must be unique."""
    tx1 = Transaction(
        chain_id='1',
        tx_hash='0x123',
        status='pending',
        data={}
    )
    db_session.add(tx1)
    db_session.commit()

    tx2 = Transaction(
        chain_id='1',
        tx_hash='0x123',
        status='pending',
        data={}
    )
    db_session.add(tx2)
    with pytest.raises(Exception):  # SQLAlchemy will raise an integrity error
        db_session.commit()
