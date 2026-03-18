"""Teaching strategies for different learning situations."""

from enum import Enum
from typing import Optional


class TeachingStrategy(str, Enum):
    """Different pedagogical approaches for different situations."""

    # Correction strategies
    IMMEDIATE_CORRECTION = "immediate_correction"  # Correct right away
    DELAYED_CORRECTION = "delayed_correction"  # Summarize corrections at end
    GENTLE_RECAST = "gentle_recast"  # Reformulate without explicit correction
    PROMPT_SELF_CORRECTION = "prompt_self_correction"  # Hint that there's an error

    # Introduction strategies
    Scaffolding = "scaffolding"  # Build on known structures
    Contextual_introduction = "contextual_introduction"  # Introduce in natural context
    Explicit_explanation = "explicit_explanation"  # Direct explanation with examples
    Pattern_highlighting = "pattern_highlighting"  # Draw attention to pattern

    # Practice strategies
    SPACED_REPETITION = "spaced_repetition"  # Review at intervals
    CONTEXTUAL_PRACTICE = "contextual_practice"  # Use in varied contexts
    CONTROLLED_PRACTICE = "controlled_practice"  # Structured drills
    FREE_PRACTICE = "free_practice"  # Open conversation

    # Flow strategies
    FLOW_PRESERVATION = "flow_preservation"  # Don't interrupt for minor errors
    CONFIDENCE_BUILDING = "confidence_building"  # Focus on what they do well
    CHALLENGE_PROVIDING = "challenge_providing"  # Push slightly beyond comfort
    COMFORT_ZONE = "comfort_zone"  # Stay in familiar territory


class StrategySelector:
    """
    Selects appropriate teaching strategy based on learner state and context.

    This is where the "art" of teaching lives - making nuanced decisions about
    when to correct, when to introduce new material, and how to balance
    accuracy with fluency.
    """

    @staticmethod
    def select_correction_strategy(
        error_severity: str,
        learner_confidence: str,
        conversation_flow: bool,
        error_type: str,
    ) -> TeachingStrategy:
        """
        Decide how to handle an error.

        Args:
            error_severity: "minor", "moderate", "major"
            learner_confidence: "very_low", "low", "moderate", "high", "very_high"
            conversation_flow: True if conversation is flowing well
            error_type: Type of error (grammar, vocabulary, pronunciation)

        Returns:
            TeachingStrategy to use
        """
        # Major errors always need addressing
        if error_severity == "major":
            if learner_confidence in ["very_low", "low"]:
                return TeachingStrategy.GENTLE_RECAST
            return TeachingStrategy.IMMEDIATE_CORRECTION

        # Moderate errors
        if error_severity == "moderate":
            if not conversation_flow:
                return TeachingStrategy.IMMEDIATE_CORRECTION
            if learner_confidence in ["high", "very_high"]:
                return TeachingStrategy.PROMPT_SELF_CORRECTION
            return TeachingStrategy.GENTLE_RECAST

        # Minor errors
        if error_severity == "minor":
            if conversation_flow and learner_confidence in ["low", "very_low"]:
                return TeachingStrategy.FLOW_PRESERVATION
            if learner_confidence in ["high", "very_high"]:
                return TeachingStrategy.PROMPT_SELF_CORRECTION
            return TeachingStrategy.DELAYED_CORRECTION

        return TeachingStrategy.FLOW_PRESERVATION

    @staticmethod
    def select_introduction_strategy(
        learner_level: str,
        pattern_difficulty: int,
        related_mastery: float,
        learner_confidence: str,
    ) -> TeachingStrategy:
        """
        Decide how to introduce new material.

        Args:
            learner_level: CEFR level (A1, A2, B1, etc.)
            pattern_difficulty: 1-5 difficulty rating
            related_mastery: Mastery of related patterns (0.0-1.0)
            learner_confidence: Current confidence level

        Returns:
            TeachingStrategy to use
        """
        # If learner is struggling, stay simple
        if learner_confidence in ["very_low", "low"]:
            return TeachingStrategy.COMFORT_ZONE

        # If related patterns are mastered, can scaffold
        if related_mastery > 0.8:
            return TeachingStrategy.Scaffolding

        # If within appropriate difficulty range
        if pattern_difficulty <= 2:
            return TeachingStrategy.Contextual_introduction
        elif pattern_difficulty <= 4:
            if learner_confidence in ["high", "very_high"]:
                return TeachingStrategy.Pattern_highlighting
            return TeachingStrategy.Explicit_explanation

        # Advanced material
        return TeachingStrategy.COMFORT_ZONE

    @staticmethod
    def should_introduce_new(
        recent_turns: int,
        recent_errors: int,
        current_vocabulary_size: int,
        time_since_last_introduction: int,
    ) -> bool:
        """
        Decide if it's a good time to introduce new material.

        Args:
            recent_turns: Number of conversation turns in current session
            recent_errors: Errors in recent turns
            current_vocabulary_size: Total vocabulary items known
            time_since_last_introduction: Minutes since last new material

        Returns:
            True if good time to introduce new material
        """
        # Don't overwhelm with new material early on
        if current_vocabulary_size < 20 and recent_turns < 10:
            return recent_turns % 5 == 0  # Every 5 turns

        # Error rate check
        error_rate = recent_errors / max(recent_turns, 1)
        if error_rate > 0.4:
            return False  # Too many errors, consolidate first

        # Spaced introduction
        if time_since_last_introduction < 3:
            return False  # Too soon

        # Every 8-12 turns is a good rhythm
        return recent_turns % 10 == 0 and recent_turns > 5

    @staticmethod
    def should_recycle_material(
        learner: object,
        material_type: str,
        min_mastery: float = 0.6,
    ) -> bool:
        """
        Decide if we should recycle/review old material.

        Args:
            learner: Learner object
            material_type: "vocabulary" or "grammar"
            min_mastery: Minimum mastery threshold to consider recycling

        Returns:
            True if should recycle material
        """
        if material_type == "vocabulary":
            to_review = learner.get_vocabulary_to_review()
            return len(to_review) > 3

        elif material_type == "grammar":
            weak_areas = learner.get_weak_grammar_areas(threshold=min_mastery)
            return len(weak_areas) > 0

        return False

    @staticmethod
    def adjust_response_length(
        learner_confidence: str,
        error_rate: float,
        turn_number: int,
    ) -> str:
        """
        Decide on appropriate response length.

        Args:
            learner_confidence: Current confidence level
            error_rate: Recent error rate
            turn_number: Current turn in conversation

        Returns:
            "short", "medium", or "long"
        """
        # Early in conversation, stay medium
        if turn_number < 3:
            return "medium"

        # High error rate or low confidence -> shorter
        if error_rate > 0.5 or learner_confidence in ["very_low", "low"]:
            return "short"

        # High confidence, low error rate -> can go longer
        if learner_confidence in ["high", "very_high"] and error_rate < 0.2:
            return "long"

        return "medium"
