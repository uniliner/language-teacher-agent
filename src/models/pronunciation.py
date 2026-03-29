"""Pronunciation tracking models."""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from dataclasses import field

from pydantic import BaseModel, Field


class PronunciationCategory(str, Enum):
    """Categories of pronunciation patterns."""

    VOWELS = "vowels"  # Including umlauts, diphthongs
    CONSONANTS = "consonants"  # Including ch, j, r, etc.
    WORD_STRESS = "word_stress"  # Stress patterns
    INTONATION = "intonation"  # Sentence-level patterns
    SOUND_COMBINATIONS = "sound_combinations"  # Cluster sounds, etc.


class PronunciationPattern(BaseModel):
    """
    A pronunciation pattern with learning state.

    Similar to VocabularyItem, this tracks:
    - Pattern information (what sound/rule it teaches)
    - Examples (words demonstrating the pattern)
    - Teaching content (how to explain it)
    - Progress tracking (mastery, spaced repetition)
    """

    # Identity
    pattern_id: str  # e.g., "umlaut_ae", "ich_laut"
    name: str  # e.g., "ICH-Laut (soft ch)"
    category: PronunciationCategory
    difficulty: str  # CEFR level: "A1", "A2", "B1", etc.

    # Teaching content
    description: str  # "The soft 'ch' sound like in 'ich'"
    examples: List[str] = Field(default_factory=list)  # ["ich", "mich", "licht", "nicht"]
    teaching_notes: str  # "Touch tongue to roof of mouth..."
    common_mistakes: List[str] = Field(default_factory=list)  # ["Pronouncing like 'k'"]

    # IPA representation (optional but helpful)
    ipa_symbol: Optional[str] = None  # e.g., /ç/ for ICH-Laut
    sound_description: Optional[str] = None  # "voiceless palatal fricative"

    # Progress tracking
    mastery_score: float = 0.0  # 0.0 to 1.0
    practice_count: int = 0
    correct_practices: int = 0
    last_practice: Optional[datetime] = None

    # Spaced repetition (SM-2 algorithm like VocabularyItem)
    next_review: Optional[datetime] = None
    ease_factor: float = 2.5
    interval: int = 0  # Days until next review

    # Context
    encountered_in_words: List[str] = Field(default_factory=list)  # Words where this appears

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def record_practice(self, quality: int) -> None:
        """
        Record a practice attempt using spaced repetition.

        Args:
            quality: 0-5 rating (0=complete failure, 5=perfect)
        """
        self.practice_count += 1
        self.last_practice = datetime.now()

        if quality >= 3:  # Success threshold
            self.correct_practices += 1

        # Update spaced repetition schedule (SM-2 algorithm)
        self._update_spaced_repetition(quality)
        self._update_mastery()
        self.updated_at = datetime.now()

    def encounter_in_word(self, word: str) -> None:
        """
        Record encountering this pattern in a word.

        Args:
            word: The word where this pattern appeared
        """
        if word and word not in self.encountered_in_words:
            self.encountered_in_words.append(word)
            self.updated_at = datetime.now()

    def _update_spaced_repetition(self, quality: int) -> None:
        """Update spaced repetition schedule using SM-2 algorithm."""
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
            # Reset on poor performance
            self.interval = 0
            self.ease_factor = max(1.3, self.ease_factor - 0.2)

        # Schedule next review
        from datetime import timedelta
        self.next_review = datetime.now() + timedelta(days=self.interval)

    def _update_mastery(self) -> None:
        """Update mastery score based on practice performance."""
        if self.practice_count == 0:
            self.mastery_score = 0.0
            return

        # Success rate
        success_rate = self.correct_practices / self.practice_count

        # Base score from success rate
        base_score = success_rate

        # Boost for consistent practice
        practice_factor = min(self.practice_count / 10, 1.0)  # Caps at 10 practices

        # Combine: 70% success rate, 30% practice consistency
        self.mastery_score = base_score * 0.7 + practice_factor * 0.3

    @property
    def is_due_for_review(self) -> bool:
        """Check if this pattern is due for review."""
        if not self.next_review:
            return True  # Never practiced
        return datetime.now() >= self.next_review

    class Config:
        use_enum_values = True
