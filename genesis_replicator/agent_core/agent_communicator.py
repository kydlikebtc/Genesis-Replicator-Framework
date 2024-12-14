"""
Agent Communicator Module

This module handles communication between agents in the Genesis Replicator Framework.
It provides messaging, event handling, and coordination capabilities.
"""
from typing import Dict, Optional, Any, List, Callable
import logging
import asyncio
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MessagePriority(Enum):
    """Enumeration of message priority levels"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3

@dataclass
class Message:
    """Data class for agent messages"""
    sender: str
    recipient: str
    content: Any
    message_type: str
    priority: MessagePriority
    timestamp: datetime
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None

class AgentCommunicator:
    """
    Manages communication between agents with support for different message types and priorities.

    Attributes:
        message_handlers (Dict): Registered message handlers by type
        message_queues (Dict): Message queues by agent
        subscriptions (Dict): Topic subscriptions by agent
    """

    def __init__(self):
        """Initialize the AgentCommunicator."""
        self.message_handlers: Dict[str, Dict[str, List[Callable]]] = {}
        self.message_queues: Dict[str, asyncio.Queue] = {}
        self.subscriptions: Dict[str, List[str]] = {}
        logger.info("AgentCommunicator initialized")

    async def register_agent(self, agent_id: str) -> bool:
        """
        Register an agent for communication.

        Args:
            agent_id (str): Agent identifier

        Returns:
            bool: Success status
        """
        try:
            if agent_id in self.message_queues:
                logger.warning(f"Agent {agent_id} already registered")
                return False

            self.message_queues[agent_id] = asyncio.Queue()
            self.message_handlers[agent_id] = {}
            self.subscriptions[agent_id] = []
            logger.info(f"Agent {agent_id} registered for communication")
            return True

        except Exception as e:
            logger.error(f"Failed to register agent {agent_id}: {str(e)}")
            return False

    async def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent from communication.

        Args:
            agent_id (str): Agent identifier

        Returns:
            bool: Success status
        """
        try:
            if agent_id not in self.message_queues:
                return False

            # Clean up agent resources
            self.message_queues.pop(agent_id)
            self.message_handlers.pop(agent_id, None)
            self.subscriptions.pop(agent_id, None)

            logger.info(f"Agent {agent_id} unregistered from communication")
            return True

        except Exception as e:
            logger.error(f"Error unregistering agent {agent_id}: {str(e)}")
            return False

    async def send_message(
        self,
        sender: str,
        recipient: str,
        content: Any,
        message_type: str,
        priority: MessagePriority = MessagePriority.NORMAL,
        correlation_id: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> bool:
        """
        Send a message to another agent.

        Args:
            sender (str): Sender agent ID
            recipient (str): Recipient agent ID
            content (Any): Message content
            message_type (str): Type of message
            priority (MessagePriority): Message priority
            correlation_id (Optional[str]): Correlation ID for related messages
            reply_to (Optional[str]): Reply-to address

        Returns:
            bool: Success status
        """
        try:
            if recipient not in self.message_queues:
                logger.error(f"Recipient agent {recipient} not registered")
                return False

            message = Message(
                sender=sender,
                recipient=recipient,
                content=content,
                message_type=message_type,
                priority=priority,
                timestamp=datetime.now(),
                correlation_id=correlation_id,
                reply_to=reply_to
            )

            await self.message_queues[recipient].put(message)
            logger.debug(f"Message sent from {sender} to {recipient}")
            return True

        except Exception as e:
            logger.error(f"Error sending message from {sender} to {recipient}: {str(e)}")
            return False

    async def receive_message(
        self,
        agent_id: str,
        timeout: Optional[float] = None
    ) -> Optional[Message]:
        """
        Receive a message for an agent.

        Args:
            agent_id (str): Agent identifier
            timeout (Optional[float]): Timeout in seconds

        Returns:
            Optional[Message]: Received message or None if timeout
        """
        try:
            if agent_id not in self.message_queues:
                logger.error(f"Agent {agent_id} not registered")
                return None

            try:
                message = await asyncio.wait_for(
                    self.message_queues[agent_id].get(),
                    timeout=timeout
                )
                logger.debug(f"Message received by {agent_id}")
                return message
            except asyncio.TimeoutError:
                return None

        except Exception as e:
            logger.error(f"Error receiving message for agent {agent_id}: {str(e)}")
            return None

    def register_handler(
        self,
        agent_id: str,
        message_type: str,
        handler: Callable[[Message], None]
    ) -> bool:
        """
        Register a message handler for an agent.

        Args:
            agent_id (str): Agent identifier
            message_type (str): Type of message to handle
            handler (Callable): Handler function

        Returns:
            bool: Success status
        """
        try:
            if agent_id not in self.message_handlers:
                logger.error(f"Agent {agent_id} not registered")
                return False

            if message_type not in self.message_handlers[agent_id]:
                self.message_handlers[agent_id][message_type] = []

            self.message_handlers[agent_id][message_type].append(handler)
            logger.info(f"Handler registered for agent {agent_id} and message type {message_type}")
            return True

        except Exception as e:
            logger.error(f"Error registering handler for agent {agent_id}: {str(e)}")
            return False

    def unregister_handler(
        self,
        agent_id: str,
        message_type: str,
        handler: Callable[[Message], None]
    ) -> bool:
        """
        Unregister a message handler.

        Args:
            agent_id (str): Agent identifier
            message_type (str): Type of message
            handler (Callable): Handler function

        Returns:
            bool: Success status
        """
        try:
            if (agent_id not in self.message_handlers or
                message_type not in self.message_handlers[agent_id]):
                return False

            handlers = self.message_handlers[agent_id][message_type]
            if handler in handlers:
                handlers.remove(handler)
                logger.info(f"Handler unregistered for agent {agent_id} and message type {message_type}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error unregistering handler for agent {agent_id}: {str(e)}")
            return False

    async def subscribe_to_topic(
        self,
        agent_id: str,
        topic: str
    ) -> bool:
        """
        Subscribe an agent to a topic.

        Args:
            agent_id (str): Agent identifier
            topic (str): Topic to subscribe to

        Returns:
            bool: Success status
        """
        try:
            if agent_id not in self.subscriptions:
                logger.error(f"Agent {agent_id} not registered")
                return False

            if topic not in self.subscriptions[agent_id]:
                self.subscriptions[agent_id].append(topic)
                logger.info(f"Agent {agent_id} subscribed to topic {topic}")
            return True

        except Exception as e:
            logger.error(f"Error subscribing agent {agent_id} to topic {topic}: {str(e)}")
            return False

    async def unsubscribe_from_topic(
        self,
        agent_id: str,
        topic: str
    ) -> bool:
        """
        Unsubscribe an agent from a topic.

        Args:
            agent_id (str): Agent identifier
            topic (str): Topic to unsubscribe from

        Returns:
            bool: Success status
        """
        try:
            if agent_id not in self.subscriptions:
                return False

            if topic in self.subscriptions[agent_id]:
                self.subscriptions[agent_id].remove(topic)
                logger.info(f"Agent {agent_id} unsubscribed from topic {topic}")
            return True

        except Exception as e:
            logger.error(f"Error unsubscribing agent {agent_id} from topic {topic}: {str(e)}")
            return False

    async def publish_to_topic(
        self,
        sender: str,
        topic: str,
        content: Any,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> bool:
        """
        Publish a message to a topic.

        Args:
            sender (str): Sender agent ID
            topic (str): Topic to publish to
            content (Any): Message content
            priority (MessagePriority): Message priority

        Returns:
            bool: Success status
        """
        try:
            success = True
            for agent_id, topics in self.subscriptions.items():
                if topic in topics and agent_id != sender:
                    message_sent = await self.send_message(
                        sender=sender,
                        recipient=agent_id,
                        content=content,
                        message_type=f"topic_{topic}",
                        priority=priority
                    )
                    success = success and message_sent
            return success

        except Exception as e:
            logger.error(f"Error publishing to topic {topic}: {str(e)}")
            return False
