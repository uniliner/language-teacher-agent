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

    def __init__(self, learner: Learner, experimentation_mode: bool = False):
        self.learner = learner
        self.selector = StrategySelector()
        self.experimentation_mode = experimentation_mode

        # Conversation state
        self.current_mode: InteractionMode = InteractionMode.CONVERSATION
        self.turn_count = 0
        self.error_count = 0
        self.session_start = datetime.now()
        self.last_introduction_time = datetime.now()
        self.last_pronunciation_time = datetime.now()
        self.last_pronunciation_turn = 0  # Track turn number when we last taught pronunciation
        self.conversation_flow_score = 0.5  # 0.0 = struggling, 1.0 = flowing

        # Configuration
        self.max_errors_before_simplify = 5
        self.flow_threshold = 0.6  # Below this, prioritize flow

        # Experimentation mode: faster triggers for testing
        if self.experimentation_mode:
            self._introduction_interval = 2  # Every 2 turns instead of 5-10
            self._review_interval = 3  # Every 3 turns instead of 8
            self._pronunciation_interval = 3  # Every 3 turns for testing
            self._min_intro_time = 0.5  # 30 seconds instead of 3 minutes
        else:
            self._introduction_interval = 10  # Normal: every 10 turns
            self._review_interval = 8  # Normal: every 8 turns
            self._pronunciation_interval = 15  # Normal: every 15 turns
            self._min_intro_time = 3  # Normal: 3 minutes

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

        # Check if we should teach pronunciation
        if self._should_teach_pronunciation(conversation_state):
            return self._create_pronunciation_decision(conversation_state)

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

        if self.experimentation_mode:
            # Fast-track for experimentation: check every few turns
            if time_since_intro < self._min_intro_time:
                return False
            return self.turn_count % self._introduction_interval == 0 and self.turn_count > 1

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

        # Check review timing based on mode
        if self.experimentation_mode:
            # More frequent review in experimentation mode
            review_due = self.turn_count % self._review_interval == 0 and self.turn_count > 1
        else:
            # Normal: every ~8 turns
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

        # Determine what to introduce based on learner's weak areas
        weak_grammar = self.learner.get_weak_grammar_areas(threshold=0.5)

        # Prioritize grammar if there are weak areas, otherwise vocabulary
        if weak_grammar and len(weak_grammar) > 0:
            # Introduce the next grammar pattern from curriculum
            introduction_type = "grammar"
            pattern = weak_grammar[0]  # Focus on weakest area

            # Select strategy based on difficulty and learner confidence
            difficulty = getattr(pattern, "difficulty_level", 2)
            if difficulty >= 4 or self.learner.confidence in [ConfidenceLevel.LOW, ConfidenceLevel.VERY_LOW]:
                strategy = TeachingStrategy.Explicit_explanation
            elif difficulty >= 3 or self.learner.confidence == ConfidenceLevel.MODERATE:
                strategy = TeachingStrategy.Pattern_highlighting
            else:
                strategy = TeachingStrategy.Contextual_introduction

            metadata = {
                "introduction_type": "grammar",
                "current_level": self.learner.current_cefr_level,
                "conversation_topic": conversation_state.get("topic", "general"),
                "grammar_pattern": pattern.name if hasattr(pattern, "name") else str(pattern),
                "pattern_description": pattern.description if hasattr(pattern, "description") else "",
            }
        else:
            # Default to vocabulary introduction
            introduction_type = "vocabulary"
            strategy = TeachingStrategy.Contextual_introduction

            metadata = {
                "introduction_type": "vocabulary",
                "current_level": self.learner.current_cefr_level,
                "conversation_topic": conversation_state.get("topic", "general"),
            }

        return TeachingDecision(
            action="introduce",
            strategy=strategy,
            content=None,  # LLM will generate this
            metadata=metadata,
        )

    def _create_review_decision(self, conversation_state: Dict[str, Any]) -> TeachingDecision:
        """Create a decision to review/recycle material."""
        # Pick something to review
        vocab_to_review = self.learner.get_vocabulary_to_review()
        weak_grammar = self.learner.get_weak_grammar_areas(threshold=0.6)

        # Decide what to review and select appropriate strategy
        if weak_grammar and len(weak_grammar) > 0:
            # Review grammar - use explicit strategies for weak areas
            review_type = "grammar"
            pattern = weak_grammar[0]
            difficulty = getattr(pattern, "difficulty_level", 2)
            mastery = pattern.mastery_score if hasattr(pattern, "mastery_score") else 0.5

            # If mastery is very low, use explicit explanation
            if mastery < 0.4 or difficulty >= 4:
                strategy = TeachingStrategy.Explicit_explanation
            elif mastery < 0.6:
                strategy = TeachingStrategy.Pattern_highlighting
            else:
                strategy = TeachingStrategy.SPACED_REPETITION

            metadata = {
                "review_type": "grammar",
                "patterns": [p.name for p in weak_grammar[:2]],
                "pattern_descriptions": [p.description for p in weak_grammar[:2] if hasattr(p, "description")],
                "mastery_scores": [round(p.mastery_score, 2) for p in weak_grammar[:2] if hasattr(p, "mastery_score")],
            }
        elif vocab_to_review:
            # Review vocabulary - use spaced repetition
            review_type = "vocabulary"
            strategy = TeachingStrategy.SPACED_REPETITION

            metadata = {
                "review_type": "vocabulary",
                "items": [v.word for v in vocab_to_review[:3]],
            }
        else:
            # Default to vocabulary review
            review_type = "vocabulary"
            strategy = TeachingStrategy.SPACED_REPETITION

            metadata = {
                "review_type": "vocabulary",
                "items": [],
            }

        return TeachingDecision(
            action="review",
            strategy=strategy,
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

    def _should_teach_pronunciation(
        self,
        conversation_state: Dict[str, Any],
    ) -> bool:
        """
        Decide if it's a good time to teach pronunciation.

        Strategic decision: Is NOW a good time to teach pronunciation?

        Consider:
        - Conversation flow (don't interrupt if flow < 0.4)
        - Learner confidence (don't overwhelm if VERY_LOW)
        - Teaching frequency (not too often - every ~15 turns)
        - Pattern availability (are there patterns to teach?)

        Args:
            conversation_state: Current conversation context

        Returns:
            True if should teach pronunciation
        """
        # Don't interrupt struggling conversations
        if self.conversation_flow_score < 0.4:
            return False

        # Don't overwhelm low-confidence learners
        if self.learner.confidence in [ConfidenceLevel.VERY_LOW, ConfidenceLevel.LOW]:
            return False

        # Don't teach too frequently
        turns_since = self._turns_since_last_pronunciation()
        if turns_since < self._pronunciation_interval:
            return False

        # Do we have patterns due for review?
        if self._has_patterns_due_for_review():
            return True

        # Do we have new patterns to introduce?
        if self._has_new_pronunciation_patterns():
            # In experimentation mode, introduce new patterns more quickly
            if self.experimentation_mode:
                return self.turn_count >= 2 and self.turn_count % self._pronunciation_interval == 0
            else:
                # Normal: wait a bit longer and check interval
                return self.turn_count > 5 and self.turn_count % self._pronunciation_interval == 0

        return False

    def _turns_since_last_pronunciation(self) -> int:
        """Get number of turns since last pronunciation teaching."""
        # In experimentation mode, use turn count tracking
        if self.experimentation_mode:
            return self.turn_count - self.last_pronunciation_turn

        # Normal mode: time-based check
        time_since = (datetime.now() - self.last_pronunciation_time).total_seconds() / 60
        return int(time_since)  # Returns minutes since last pronunciation teaching

    def _has_patterns_due_for_review(self) -> bool:
        """Check if learner has pronunciation patterns due for review."""
        if not hasattr(self.learner, "pronunciation_patterns"):
            return False

        now = datetime.now()
        for pattern in self.learner.pronunciation_patterns.values():
            if pattern.is_due_for_review and pattern.mastery_score < 0.8:
                return True

        return False

    def _has_new_pronunciation_patterns(self) -> bool:
        """Check if there are new pronunciation patterns to introduce."""
        if not hasattr(self.learner, "pronunciation_patterns"):
            return True  # Learner hasn't started pronunciation yet

        # Check if there are patterns in database that learner hasn't seen
        # We assume if learner has < 10 patterns, there are more to learn
        return len(self.learner.pronunciation_patterns) < 10

    def _create_pronunciation_decision(
        self,
        conversation_state: Dict[str, Any],
    ) -> TeachingDecision:
        """
        Create a decision to teach pronunciation.

        Args:
            conversation_state: Current conversation context

        Returns:
            TeachingDecision for pronunciation teaching
        """
        self.last_pronunciation_time = datetime.now()
        self.last_pronunciation_turn = self.turn_count  # Track the turn we taught pronunciation

        metadata = {
            "teaching_type": "pronunciation",
            "current_level": self.learner.current_cefr_level,
            "conversation_topic": conversation_state.get("topic", "general"),
            "confidence_level": self.learner.confidence,
        }

        return TeachingDecision(
            action="teach_pronunciation",
            strategy=TeachingStrategy.PRONUNCIATION_TEACHING,
            content=None,  # Agent will generate this
            metadata=metadata,
        )

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
            "experimentation_mode": self.experimentation_mode,
        }
