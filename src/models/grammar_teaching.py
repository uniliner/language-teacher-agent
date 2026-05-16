"""Grammar teaching models for tracking pedagogical effectiveness."""

from dataclasses import dataclass, asdict
from typing import Dict, List, Literal, Optional, Any
from pydantic import BaseModel, Field


@dataclass
class StrategyStats:
    """Track effectiveness of a teaching strategy.

    Uses @dataclass (not Pydantic BaseModel) per the design decision:
    - Simple aggregation stats, no complex validation needed
    - Clean serialization with dataclasses.asdict()
    - Avoids awkward model_dump() calls in persistence code
    """
    strategy_name: str
    attempts: int = 0
    successful_corrections: int = 0  # learner used correctly next time
    learner_engagement: float = 0.0  # did learner try to use it?
    avg_mastery_improvement: float = 0.0

    @property
    def success_rate(self) -> float:
        """Calculate success rate (0.0 to 1.0)."""
        return self.successful_corrections / max(self.attempts, 1)


class LearnerGrammarProfile(BaseModel):
    """
    Learn about this learner's grammar learning characteristics.

    Uses Pydantic BaseModel per the design decision:
    - Needs validation for learning_style and explanation_length fields
    - Has nested structures that benefit from Pydantic's validation
    - Persistence via .model_dump() for JSON serialization
    """
    # Learning style (detected from interactions)
    learning_style: Literal["analytical", "visual", "immersion", "unknown"] = "unknown"
    preferred_explanation_length: Literal["brief", "detailed", "adaptive"] = "adaptive"

    # What works for this learner
    effective_teaching_methods: List[str] = Field(default_factory=list)
    ineffective_teaching_methods: List[str] = Field(default_factory=list)

    # Grammar patterns
    error_prone_patterns: List[str] = Field(default_factory=list)  # patterns with high error rate
    strength_patterns: List[str] = Field(default_factory=list)  # patterns mastered quickly
    problematic_pattern_combinations: List[tuple[str, str]] = Field(default_factory=list)

    # Learning patterns
    avg_attempts_to_mastery: float = 0.0
    retention_rate: float = 0.0  # how well they remember
    practice_frequency_preference: str = "adaptive"
    optimal_teaching_frequency: str = "adaptive"  # e.g., "every_10_turns", "every_15_turns"

    def update_learning_style(self, detected_style: str) -> None:
        """
        Update learning style from detection.

        This is called by the agent's _detect_learning_style() method.
        The agent owns the LLM client; the model just stores the result.

        Args:
            detected_style: The detected learning style
        """
        if detected_style in ["analytical", "visual", "immersion"]:
            self.learning_style = detected_style

    def update_from_teaching_result(
        self,
        pattern: str,
        strategy: str,
        success: bool,
        pattern_mastery_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update profile based on teaching effectiveness.

        IMPLEMENTATION: Track patterns and strategies

        Args:
            pattern: Pattern name that was taught
            strategy: Teaching strategy used
            success: Whether the teaching was effective
            pattern_mastery_data: Optional dict with pattern stats {
                "attempts": int,
                "mastery_score": float
            }
        """
        if success:
            # Track effective strategies
            if strategy not in self.effective_teaching_methods:
                self.effective_teaching_methods.append(strategy)

            # Remove from ineffective if it's there
            if strategy in self.ineffective_teaching_methods:
                self.ineffective_teaching_methods.remove(strategy)

            # Track strength patterns (mastered quickly)
            # pattern_mastery_data is passed in from the agent
            if pattern_mastery_data:
                attempts = pattern_mastery_data.get("attempts", 0)
                mastery_score = pattern_mastery_data.get("mastery_score", 0.0)

                # If mastered in 3 or fewer attempts with good mastery
                if attempts <= 3 and mastery_score >= 0.7:
                    if pattern not in self.strength_patterns:
                        self.strength_patterns.append(pattern)

        else:
            # Track ineffective strategies (only if we have comparison data)
            if strategy not in self.ineffective_teaching_methods and len(self.effective_teaching_methods) > 0:
                # Only mark as ineffective if we have comparison data
                if strategy not in self.effective_teaching_methods:
                    self.ineffective_teaching_methods.append(strategy)

            # Track error-prone patterns
            if pattern not in self.error_prone_patterns:
                self.error_prone_patterns.append(pattern)
