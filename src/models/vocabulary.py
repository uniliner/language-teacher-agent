"""Vocabulary tracking models."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class VocabularyStatus(str, Enum):
    """Mastery level of a vocabulary item."""

    NEW = "new"  # Never encountered
    ENCOUNTERED = "encountered"  # Seen but not actively used
    RECOGNIZED = "recognized"  # Can understand in context
    PRODUCTION = "production"  # Can use in speech/writing
    MASTERED = "mastered"  # Consistently correct


class VocabularyItem(BaseModel):
    """A single vocabulary item with learning state."""

    word: str
    translation: str
    part_of_speech: str  # noun, verb, adjective, etc.
    language: str = "german"

    # Learning state
    status: VocabularyStatus = VocabularyStatus.NEW
    encounters_count: int = 0
    correct_productions: int = 0
    incorrect_productions: int = 0

    # Spaced repetition
    last_seen: Optional[datetime] = None
    last_reviewed: Optional[datetime] = None
    next_review: Optional[datetime] = None
    ease_factor: float = 2.5  # SM-2 algorithm
    interval: int = 0  # Days until next review

    # Context
    example_sentences: list[str] = Field(default_factory=list)
    contexts_seen: list[str] = Field(default_factory=list)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def record_encounter(self, context: str = "") -> None:
        """Record a new encounter with this word."""
        self.encounters_count += 1
        self.last_seen = datetime.now()
        if context and context not in self.contexts_seen:
            self.contexts_seen.append(context)
        self._update_status()
        self.updated_at = datetime.now()

    def record_production(self, correct: bool) -> None:
        """Record a production attempt by the learner."""
        if correct:
            self.correct_productions += 1
        else:
            self.incorrect_productions += 1
        self._update_status()
        self.updated_at = datetime.now()

    def update_spaced_repetition(self, quality: int) -> None:
        """
        Update spaced repetition schedule using SM-2 algorithm.

        Args:
            quality: 0-5 rating of recall (0=complete failure, 5=perfect)
        """
        self.last_reviewed = datetime.now()

        # SM-2 algorithm
        if quality >= 3:
            if self.interval == 0:
                self.interval = 1
            elif self.interval == 1:
                self.interval = 6
            else:
                self.interval = int(self.interval * self.ease_factor)

            self.ease_factor = max(
                1.3,
                self.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
            )
        else:
            self.interval = 0
            self.ease_factor = max(1.3, self.ease_factor - 0.2)

        # Schedule next review
        from datetime import timedelta
        self.next_review = datetime.now() + timedelta(days=self.interval)
        self.updated_at = datetime.now()

    def _update_status(self) -> None:
        """Update mastery status based on performance."""
        success_rate = 0.0
        if self.correct_productions + self.incorrect_productions > 0:
            success_rate = self.correct_productions / (
                self.correct_productions + self.incorrect_productions
            )

        if self.status == VocabularyStatus.NEW:
            if self.encounters_count >= 3:
                self.status = VocabularyStatus.ENCOUNTERED
        elif self.status == VocabularyStatus.ENCOUNTERED:
            if self.encounters_count >= 5:
                self.status = VocabularyStatus.RECOGNIZED
        elif self.status == VocabularyStatus.RECOGNIZED:
            if self.correct_productions >= 3 and success_rate >= 0.7:
                self.status = VocabularyStatus.PRODUCTION
        elif self.status == VocabularyStatus.PRODUCTION:
            if self.correct_productions >= 10 and success_rate >= 0.9:
                self.status = VocabularyStatus.MASTERED
            elif self.incorrect_productions > self.correct_productions:
                # Regression
                self.status = VocabularyStatus.RECOGNIZED

    @property
    def mastery_score(self) -> float:
        """Calculate overall mastery score (0.0 to 1.0)."""
        status_scores = {
            VocabularyStatus.NEW: 0.0,
            VocabularyStatus.ENCOUNTERED: 0.2,
            VocabularyStatus.RECOGNIZED: 0.5,
            VocabularyStatus.PRODUCTION: 0.75,
            VocabularyStatus.MASTERED: 1.0,
        }
        base_score = status_scores[self.status]

        # Adjust with performance data
        if self.correct_productions + self.incorrect_productions > 0:
            success_rate = self.correct_productions / (
                self.correct_productions + self.incorrect_productions
            )
            # Blend status and performance
            return base_score * 0.7 + success_rate * 0.3
        return base_score

    class Config:
        use_enum_values = True
