"""
History Analyzer Module

This module analyzes historical decision data to improve future
decision-making in the Genesis Replicator Framework.
"""
from typing import Dict, List, Any, Optional, Tuple
import logging
from dataclasses import dataclass
from datetime import datetime
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DecisionRecord:
    """Represents a historical decision record."""
    id: str
    timestamp: datetime
    context: Dict[str, Any]
    decision: Any
    outcome: Optional[Any] = None
    feedback_score: Optional[float] = None

class HistoryAnalyzer:
    """Analyzes historical decision data for pattern recognition and optimization."""

    def __init__(self, max_history: int = 1000):
        """
        Initialize the HistoryAnalyzer.

        Args:
            max_history: Maximum number of historical records to maintain
        """
        self.history: List[DecisionRecord] = []
        self.max_history = max_history
        self.performance_metrics: Dict[str, float] = {}
        logger.info("History Analyzer initialized")

    def record_decision(
        self,
        decision_id: str,
        context: Dict[str, Any],
        decision: Any
    ) -> None:
        """
        Record a new decision.

        Args:
            decision_id: Unique identifier for the decision
            context: Context in which the decision was made
            decision: The decision that was made
        """
        record = DecisionRecord(
            id=decision_id,
            timestamp=datetime.now(),
            context=context,
            decision=decision
        )

        self.history.append(record)
        if len(self.history) > self.max_history:
            self.history.pop(0)

        logger.info(f"Recorded decision: {decision_id}")

    def record_outcome(
        self,
        decision_id: str,
        outcome: Any,
        feedback_score: Optional[float] = None
    ) -> None:
        """
        Record the outcome of a previous decision.

        Args:
            decision_id: ID of the decision
            outcome: Outcome that resulted from the decision
            feedback_score: Optional numerical score for the decision's effectiveness
        """
        for record in self.history:
            if record.id == decision_id:
                record.outcome = outcome
                record.feedback_score = feedback_score
                logger.info(f"Recorded outcome for decision: {decision_id}")
                return

        logger.warning(f"Decision {decision_id} not found in history")

    def analyze_performance(
        self,
        time_window: Optional[Tuple[datetime, datetime]] = None
    ) -> Dict[str, float]:
        """
        Analyze decision-making performance metrics.

        Args:
            time_window: Optional time range for analysis (start, end)

        Returns:
            Dictionary of performance metrics
        """
        relevant_records = self.history
        if time_window:
            start, end = time_window
            relevant_records = [
                r for r in self.history
                if start <= r.timestamp <= end
            ]

        total_decisions = len(relevant_records)
        if total_decisions == 0:
            return {}

        scored_decisions = [
            r for r in relevant_records
            if r.feedback_score is not None
        ]

        if not scored_decisions:
            return {"total_decisions": total_decisions}

        avg_score = sum(r.feedback_score for r in scored_decisions) / len(scored_decisions)

        self.performance_metrics = {
            "total_decisions": total_decisions,
            "scored_decisions": len(scored_decisions),
            "average_score": avg_score
        }

        logger.info("Performance analysis completed")
        return self.performance_metrics

    def find_similar_decisions(
        self,
        context: Dict[str, Any],
        limit: int = 5
    ) -> List[DecisionRecord]:
        """
        Find historical decisions made in similar contexts.

        Args:
            context: Current context to compare against
            limit: Maximum number of similar decisions to return

        Returns:
            List of similar historical decisions
        """
        def calculate_similarity(record: DecisionRecord) -> float:
            """Calculate similarity score between contexts."""
            common_keys = set(context.keys()) & set(record.context.keys())
            if not common_keys:
                return 0.0

            matches = sum(
                context[key] == record.context[key]
                for key in common_keys
            )
            return matches / len(common_keys)

        similar_decisions = sorted(
            self.history,
            key=calculate_similarity,
            reverse=True
        )[:limit]

        logger.info(f"Found {len(similar_decisions)} similar decisions")
        return similar_decisions

    def export_history(self, filepath: str) -> None:
        """
        Export decision history to a JSON file.

        Args:
            filepath: Path to save the export file
        """
        export_data = []
        for record in self.history:
            export_data.append({
                "id": record.id,
                "timestamp": record.timestamp.isoformat(),
                "context": record.context,
                "decision": record.decision,
                "outcome": record.outcome,
                "feedback_score": record.feedback_score
            })

        try:
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2)
            logger.info(f"Exported history to: {filepath}")
        except Exception as e:
            logger.error(f"Error exporting history: {str(e)}")
            raise

    def clear_history(self) -> None:
        """Clear all historical records."""
        self.history.clear()
        self.performance_metrics.clear()
        logger.info("History cleared")
