"""Grammar pattern tracking models."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class GrammarWeakness(str, Enum):
    """Types of grammar weaknesses."""

    WORD_ORDER = "word_order"  # Subject-verb-object, verb position
    CASE = "case"  # Nominative, accusative, dative, genitive
    GENDER = "gender"  # Der, die, das
    VERB_CONJUGATION = "verb_conjugation"  # Person, number, tense
    ARTICLE_USAGE = "article_usage"  # Definite/indefinite articles
    PREPOSITION = "preposition"  # Preposition-case agreement
    ADJECTIVE_ENDING = "adjective_ending"  # Adjective declension
    SUBORDINATE_CLAUSE = "subordinate_clause"  # Nach, weil, dass
    SEPARABLE_VERB = "separable_verb"  # Separable prefix verbs
    PERFECT_TENSE = "perfect_tense"  # Auxiliar verb choice
    PASSIVE_VOICE = "passive_voice"  # Werden + participle


class GrammarPattern(BaseModel):
    """A grammatical pattern/structure with learning state."""

    name: str
    description: str
    category: GrammarWeakness
    examples_correct: list[str] = Field(default_factory=list)
    examples_common_errors: list[str] = Field(default_factory=list)

    # Learning state
    attempts: int = 0
    errors: int = 0
    successes: int = 0

    # Difficulty
    difficulty_level: int = Field(default=1, ge=1, le=5)  # 1=basic, 5=advanced

    # Tracking
    first_seen: Optional[datetime] = None
    last_attempt: Optional[datetime] = None
    last_error: Optional[datetime] = None

    # Context
    introduced_at_level: str = "A1"  # CEFR level when introduced
    related_patterns: list[str] = Field(default_factory=list)  # Names of related patterns

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def record_attempt(self, success: bool) -> None:
        """Record an attempt using this pattern."""
        self.attempts += 1
        self.last_attempt = datetime.now()

        if success:
            self.successes += 1
        else:
            self.errors += 1
            self.last_error = datetime.now()

        if self.first_seen is None:
            self.first_seen = datetime.now()

        self.updated_at = datetime.now()

    @property
    def error_rate(self) -> float:
        """Calculate error rate (0.0 to 1.0)."""
        if self.attempts == 0:
            return 0.0
        return self.errors / self.attempts

    @property
    def mastery_score(self) -> float:
        """
        Calculate mastery score.
        Considers success rate, recency, and attempt count.
        """
        if self.attempts == 0:
            return 0.0

        # Base score from success rate
        success_rate = 1.0 - self.error_rate

        # Boost for consistent practice
        attempt_bonus = min(self.attempts / 20, 0.2)  # Max 20% bonus

        # Decay for recent errors (errors in last 3 attempts reduce score)
        recent_errors = 0
        if self.attempts >= 3:
            # This is simplified - in production, track actual history
            if self.last_error and self.last_attempt:
                time_diff = (self.last_attempt - self.last_error).days
                if time_diff < 7:  # Error within a week
                    recent_errors = 0.1

        score = success_rate + attempt_bonus - recent_errors
        return max(0.0, min(1.0, score))

    @property
    def needs_review(self) -> bool:
        """Determine if this pattern needs review."""
        # Needs review if:
        # 1. High error rate (>40%)
        # 2. Recent error
        # 3. Low attempt count (<5)

        if self.attempts < 5:
            return True

        if self.error_rate > 0.4:
            return True

        if self.last_error:
            days_since_error = (datetime.now() - self.last_error).days
            if days_since_error < 7 and self.attempts < 10:
                return True

        return False

    class Config:
        use_enum_values = True
