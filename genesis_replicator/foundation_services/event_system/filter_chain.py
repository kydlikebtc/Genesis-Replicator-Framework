"""
Filter Chain Module

This module implements the event filtering system for the Genesis Replicator Framework.
It provides functionality for filtering events based on patterns and rules.
"""
from typing import List, Callable, Optional
from dataclasses import dataclass
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class FilterRule:
    """Represents a filter rule for event processing"""
    pattern: str
    condition: Optional[Callable] = None
    priority: int = 0
    description: str = ""

class FilterChain:
    """
    Implements event filtering logic with pattern matching and rule-based filtering.

    Attributes:
        filters (List[FilterRule]): List of filter rules
        enabled (bool): Flag to enable/disable the filter chain
    """

    def __init__(self):
        """Initialize the FilterChain with empty filters"""
        self.filters: List[FilterRule] = []
        self.enabled: bool = True
        logger.info("FilterChain initialized")

    def add_filter(self, filter_rule: FilterRule) -> None:
        """
        Add a new filter rule to the chain.

        Args:
            filter_rule (FilterRule): The filter rule to add
        """
        self.filters.append(filter_rule)
        # Sort filters by priority (higher priority first)
        self.filters.sort(key=lambda x: -x.priority)
        logger.info(f"Added filter rule: {filter_rule.description}")

    def remove_filter(self, pattern: str) -> None:
        """
        Remove a filter rule by its pattern.

        Args:
            pattern (str): Pattern of the filter to remove
        """
        self.filters = [f for f in self.filters if f.pattern != pattern]
        logger.info(f"Removed filter with pattern: {pattern}")

    def apply_filters(self, event_type: str, event_data: dict) -> bool:
        """
        Apply all filters to an event.

        Args:
            event_type (str): Type of the event
            event_data (dict): Event data to filter

        Returns:
            bool: True if event passes all filters, False otherwise
        """
        if not self.enabled:
            return True

        for filter_rule in self.filters:
            try:
                # Check pattern match
                if not re.match(filter_rule.pattern, event_type):
                    continue

                # If there's a condition function, evaluate it
                if filter_rule.condition and not filter_rule.condition(event_data):
                    logger.debug(f"Event filtered by condition in rule: {filter_rule.description}")
                    return False

            except Exception as e:
                logger.error(f"Error applying filter {filter_rule.description}: {str(e)}")
                # Continue with next filter on error
                continue

        return True

    def enable(self) -> None:
        """Enable the filter chain"""
        self.enabled = True
        logger.info("FilterChain enabled")

    def disable(self) -> None:
        """Disable the filter chain"""
        self.enabled = False
        logger.info("FilterChain disabled")
