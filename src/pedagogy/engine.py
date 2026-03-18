"""
Pedagogical decision engine.

This is the core intelligence that decides what to do next in a conversation:
- Should we introduce new vocabulary?
- Should we correct this error?
- Should we recycle old material?
- Should we stay in comfort zone or challenge the learner?
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from models.learner import Learner, ConfidenceLevel
from pedagogy.strategies import TeachingStrategy, StrategySelector


class InteractionMode(str, Enum):
    """Different modes of interaction."""

    CONVERSATION = "conversation"  # Natural flowing conversation
    TEACHING = "teaching"  # Explicit instruction/explanation
    PRACTICE = "practice"  # Structured practice
    REVIEW = "review"  # Recycling old material


@dataclass
class TeachingDecision:
    """A decision about what to do next."""

    action: str  # "continue", "correct", "introduce", "review", "simplify"
    strategy: Optional[TeachingStrategy]
    content: Optional[str]  # The actual response/content
    metadata: Dict[str, Any]  # Additional context

    # Confidence in this decision (0.0 to 1.0)
    confidence: float = 1.0

    def __str__(self) -> str:
        return f"TeachingDecision(action={self.action}, strategy={self.strategy})"


class PedagogicalEngine:
    """
    The pedagogical decision engine.

    This analyzes learner state and conversation context to make intelligent
    teaching decisions in real-time.
    """

    def __init__(self, learner: Learner):
        self.learner = learner
        self.selector = StrategySelector()

        # Conversation state
        self.current_mode: InteractionMode = InteractionMode.CONVERSATION
        self.turn_count = 0
        self.error_count = 0
        self.session_start = datetime.now()
        self.last_introduction_time = datetime.now()
        self.conversation_flow_score = 0.5  # 0.0 = struggling, 1.0 = flowing

        # Configuration
        self.max_errors_before_simplify = 5
        self.flow_threshold = 0.6  # Below this, prioritize flow

    def analyze_turn(
        self,
        learner_input: str,
        detected_errors: List[Dict[str, str]],
        conversation_state: Dict[str, Any],
    ) -> TeachingDecision:
        """
        Analyze a learner turn and decide what to do.

        Args:
            learner_input: What the learner said
            detected_errors: List of detected errors with metadata
            conversation_state: Current conversation context

        Returns:
            TeachingDecision with action and content
        """
        self.turn_count += 1

        # Update conversation flow
        self._update_flow_score(learner_input, detected_errors)

        # Calculate error rate
        recent_error_rate = self.error_count / max(self.turn_count, 1)

        # Major decision tree
        if detected_errors and self._should_correct_now(detected_errors):
            return self._create_correction_decision(detected_errors, learner_input)

        if self._should_introduce_new_material(recent_error_rate):
            return self._create_introduction_decision(conversation_state)

        if self._should_recycle_material():
            return self._create_review_decision(conversation_state)

        # Default: continue conversation
        return self._create_continuation_decision(conversation_state)

    def _update_flow_score(self, learner_input: str, errors: List[Dict]) -> None:
        """Update the conversation flow score."""
        # More errors = lower flow
        error_impact = len(errors) * 0.1

        # Short responses might indicate struggle
        length_factor = 0.0
        if len(learner_input.split()) < 3:
            length_factor = -0.1
        elif len(learner_input.split()) > 8:
            length_factor = 0.05

        # Update with decay (recent turns matter more)
        self.conversation_flow_score = (
            self.conversation_flow_score * 0.7
            + (1.0 - error_impact + length_factor) * 0.3
        )
        self.conversation_flow_score = max(0.0, min(1.0, self.conversation_flow_score))

        # Track errors
        self.error_count += len(errors)

    def _should_correct_now(self, errors: List[Dict]) -> bool:
        """Decide if we should correct errors now."""
        if not errors:
            return False

        # Always correct major errors
        major_errors = [e for e in errors if e.get("severity") == "major"]
        if major_errors:
            return True

        # If flow is very low, prioritize getting back on track
        if self.conversation_flow_score < 0.3:
            return False  # Let them speak!

        # If confidence is very low, be gentle
        if self.learner.confidence in [ConfidenceLevel.VERY_LOW, ConfidenceLevel.LOW]:
            # Only correct if it's been a while
            return self.turn_count % 3 == 0

        # Default: correct moderate+ errors
        moderate_errors = [e for e in errors if e.get("severity") in ["moderate", "major"]]
        return len(moderate_errors) > 0

    def _should_introduce_new_material(self, recent_error_rate: float) -> bool:
        """Decide if it's a good time to introduce new material."""
        time_since_intro = (datetime.now() - self.last_introduction_time).total_seconds() / 60

        return self.selector.should_introduce_new(
            recent_turns=self.turn_count,
            recent_errors=self.error_count,
            current_vocabulary_size=len(self.learner.vocabulary),
            time_since_last_introduction=time_since_intro,
        )

    def _should_recycle_material(self) -> bool:
        """Decide if we should recycle/review old material."""
        # Check vocabulary needing review
        vocab_needs_review = len(self.learner.get_vocabulary_to_review()) > 2

        # Check weak grammar areas
        weak_grammar = len(self.learner.get_weak_grammar_areas(threshold=0.6)) > 0

        # Every ~8 turns, consider review
        review_due = self.turn_count % 8 == 0 and self.turn_count > 5

        return (vocab_needs_review or weak_grammar) and review_due

    def _create_correction_decision(
        self, errors: List[Dict], learner_input: str
    ) -> TeachingDecision:
        """Create a decision to correct errors."""
        # Pick the most important error to address
        error = max(errors, key=lambda e: self._error_severity_score(e))

        # Select correction strategy
        strategy = self.selector.select_correction_strategy(
            error_severity=error.get("severity", "moderate"),
            learner_confidence=self.learner.confidence,
            conversation_flow=self.conversation_flow_score > self.flow_threshold,
            error_type=error.get("type", "grammar"),
        )

        # Build correction guidance
        metadata = {
            "error": error,
            "learner_input": learner_input,
            "strategy": strategy,
        }

        return TeachingDecision(
            action="correct",
            strategy=strategy,
            content=None,  # LLM will generate this
            metadata=metadata,
        )

    def _create_introduction_decision(
        self, conversation_state: Dict[str, Any]
    ) -> TeachingDecision:
        """Create a decision to introduce new material."""
        self.last_introduction_time = datetime.now()

        # Determine what to introduce
        # (This would integrate with curriculum in full version)
        metadata = {
            "introduction_type": "vocabulary",  # or "grammar"
            "current_level": self.learner.current_cefr_level,
            "conversation_topic": conversation_state.get("topic", "general"),
        }

        return TeachingDecision(
            action="introduce",
            strategy=TeachingStrategy.Contextual_introduction,
            content=None,  # LLM will generate this
            metadata=metadata,
        )

    def _create_review_decision(self, conversation_state: Dict[str, Any]) -> TeachingDecision:
        """Create a decision to review/recycle material."""
        # Pick something to review
        vocab_to_review = self.learner.get_vocabulary_to_review()
        weak_grammar = self.learner.get_weak_grammar_areas(threshold=0.6)

        metadata = {
            "review_type": "vocabulary" if vocab_to_review else "grammar",
            "items": [v.word for v in vocab_to_review[:3]] if vocab_to_review else [],
            "patterns": [p.name for p in weak_grammar[:2]] if weak_grammar else [],
        }

        return TeachingDecision(
            action="review",
            strategy=TeachingStrategy.SPACED_REPETITION,
            content=None,
            metadata=metadata,
        )

    def _create_continuation_decision(
        self, conversation_state: Dict[str, Any]
    ) -> TeachingDecision:
        """Create a decision to continue natural conversation."""

        # Decide on response characteristics
        response_length = self.selector.adjust_response_length(
            learner_confidence=self.learner.confidence,
            error_rate=self.error_count / max(self.turn_count, 1),
            turn_number=self.turn_count,
        )

        # Challenge or comfort?
        if self.learner.confidence in [ConfidenceLevel.HIGH, ConfidenceLevel.VERY_HIGH]:
            strategy = TeachingStrategy.CHALLENGE_PROVIDING
        elif self.learner.confidence in [ConfidenceLevel.VERY_LOW, ConfidenceLevel.LOW]:
            strategy = TeachingStrategy.CONFIDENCE_BUILDING
        else:
            strategy = TeachingStrategy.FLOW_PRESERVATION

        metadata = {
            "response_length": response_length,
            "conversation_state": conversation_state,
            "flow_score": self.conversation_flow_score,
        }

        return TeachingDecision(
            action="continue",
            strategy=strategy,
            content=None,
            metadata=metadata,
        )

    def _error_severity_score(self, error: Dict) -> float:
        """Calculate a severity score for an error."""
        severity_map = {"minor": 1.0, "moderate": 2.0, "major": 3.0}
        base = severity_map.get(error.get("severity", "moderate"), 2.0)

        # Boost score for recurring errors
        if error.get("recurring", False):
            base *= 1.5

        # Boost for critical grammar (e.g., verb position in German)
        if error.get("type") == "grammar" and error.get("critical", False):
            base *= 1.3

        return base

    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current teaching session."""
        duration = (datetime.now() - self.session_start).total_seconds() / 60

        return {
            "turns": self.turn_count,
            "errors": self.error_count,
            "error_rate": self.error_count / max(self.turn_count, 1),
            "duration_minutes": round(duration, 1),
            "flow_score": round(self.conversation_flow_score, 2),
            "mode": self.current_mode,
        }
