"""
Rule Engine Module

This module manages decision rules and their evaluation in the
Genesis Replicator Framework.
"""
from typing import Dict, List, Any, Callable, Optional
import logging
from dataclasses import dataclass
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Rule:
    """Represents a decision rule with conditions and actions."""
    id: str
    name: str
    condition: Callable[[Dict[str, Any]], bool]
    action: Callable[[Dict[str, Any]], Any]
    priority: int
    created_at: datetime
    description: str
    enabled: bool = True

class RuleEngine:
    """Manages and evaluates decision rules."""

    def __init__(self):
        """Initialize the RuleEngine."""
        self.rules: Dict[str, Rule] = {}
        logger.info("Rule Engine initialized")

    def add_rule(
        self,
        rule_id: str,
        name: str,
        condition: Callable[[Dict[str, Any]], bool],
        action: Callable[[Dict[str, Any]], Any],
        priority: int = 0,
        description: str = ""
    ) -> None:
        """
        Add a new rule to the engine.

        Args:
            rule_id: Unique identifier for the rule
            name: Human-readable name for the rule
            condition: Function that evaluates if rule should be applied
            action: Function to execute when rule conditions are met
            priority: Rule priority (higher numbers = higher priority)
            description: Description of the rule's purpose
        """
        if rule_id in self.rules:
            raise ValueError(f"Rule '{rule_id}' already exists")

        rule = Rule(
            id=rule_id,
            name=name,
            condition=condition,
            action=action,
            priority=priority,
            created_at=datetime.now(),
            description=description
        )
        self.rules[rule_id] = rule
        logger.info(f"Added rule: {name} ({rule_id})")

    def evaluate_rules(self, context: Dict[str, Any]) -> List[Any]:
        """
        Evaluate all enabled rules against the given context.

        Args:
            context: Context data for rule evaluation

        Returns:
            List of results from executed rule actions
        """
        results = []
        sorted_rules = sorted(
            [rule for rule in self.rules.values() if rule.enabled],
            key=lambda x: x.priority,
            reverse=True
        )

        for rule in sorted_rules:
            try:
                if rule.condition(context):
                    logger.debug(f"Rule {rule.name} condition met, executing action")
                    result = rule.action(context)
                    results.append(result)
                    logger.debug(f"Rule {rule.name} executed successfully")
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.name}: {str(e)}")
                continue

        return results

    def disable_rule(self, rule_id: str) -> None:
        """
        Disable a rule.

        Args:
            rule_id: ID of the rule to disable
        """
        if rule_id not in self.rules:
            raise ValueError(f"Rule '{rule_id}' not found")

        self.rules[rule_id].enabled = False
        logger.info(f"Disabled rule: {rule_id}")

    def enable_rule(self, rule_id: str) -> None:
        """
        Enable a rule.

        Args:
            rule_id: ID of the rule to enable
        """
        if rule_id not in self.rules:
            raise ValueError(f"Rule '{rule_id}' not found")

        self.rules[rule_id].enabled = True
        logger.info(f"Enabled rule: {rule_id}")

    def remove_rule(self, rule_id: str) -> None:
        """
        Remove a rule from the engine.

        Args:
            rule_id: ID of the rule to remove
        """
        if rule_id not in self.rules:
            raise ValueError(f"Rule '{rule_id}' not found")

        del self.rules[rule_id]
        logger.info(f"Removed rule: {rule_id}")

    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """
        Get a rule by its ID.

        Args:
            rule_id: ID of the rule to retrieve

        Returns:
            Rule if found, None otherwise
        """
        return self.rules.get(rule_id)

    def list_rules(self) -> List[Rule]:
        """
        Get all rules in the engine.

        Returns:
            List of all rules
        """
        return list(self.rules.values())

    def update_rule_priority(self, rule_id: str, priority: int) -> None:
        """
        Update the priority of a rule.

        Args:
            rule_id: ID of the rule to update
            priority: New priority value
        """
        if rule_id not in self.rules:
            raise ValueError(f"Rule '{rule_id}' not found")

        self.rules[rule_id].priority = priority
        logger.info(f"Updated rule {rule_id} priority to: {priority}")
