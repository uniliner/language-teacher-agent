"""Learner state model."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .vocabulary import VocabularyItem, VocabularyStatus
from .grammar import GrammarPattern
from .pronunciation import PronunciationPattern


class ConfidenceLevel(str, Enum):
    """Learner's confidence level."""

    VERY_LOW = "very_low"  # Struggling, needs encouragement
    LOW = "low"  # Hesitant, makes many errors
    MODERATE = "moderate"  # Comfortable with familiar topics
    HIGH = "high"  # Confident, attempts complex structures
    VERY_HIGH = "very_high"  # Very confident, may need challenge


class LearnerStats(BaseModel):
    """Overall learning statistics."""

    total_conversations: int = 0
    total_turns: int = 0
    total_words_encountered: int = 0

    # Vocabulary stats
    words_mastered: int = 0
    words_in_progress: int = 0
    active_vocabulary_size: int = 0

    # Grammar stats
    grammar_patterns_learned: int = 0
    grammar_patterns_struggling: int = 0

    # Recent activity
    last_conversation: Optional[datetime] = None
    current_streak_days: int = 0

    # Time tracking
    total_minutes_practiced: float = 0.0


class Learner(BaseModel):
    """
    Complete learner state.

    This is the central model that tracks everything about the learner's
    progress across vocabulary, grammar, confidence, and conversation history.
    """

    # Identity
    learner_id: str
    target_language: str = "german"
    native_language: str = "english"

    # Overall state
    confidence: ConfidenceLevel = ConfidenceLevel.MODERATE
    current_cefr_level: str = "A1"  # Self-assessed or auto-detected

    # Learning collections
    vocabulary: Dict[str, VocabularyItem] = Field(default_factory=dict)  # word -> item
    grammar_patterns: Dict[str, GrammarPattern] = Field(default_factory=dict)  # name -> pattern
    pronunciation_patterns: Dict[str, PronunciationPattern] = Field(default_factory=dict)  # pattern_id -> pattern

    # Conversation history (recent)
    recent_conversations: List[Dict[str, Any]] = Field(default_factory=list, max_length=50)

    # Pedagogical state
    topics_covered: List[str] = Field(default_factory=list)
    current_focus_areas: List[str] = Field(default_factory=list)  # grammar or vocab topics
    avoided_topics: List[str] = Field(default_factory=list)  # topics causing frustration

    # Statistics
    stats: LearnerStats = Field(default_factory=LearnerStats)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)

    # Settings
    correction_sensitivity: str = "balanced"  # strict, balanced, gentle
    preferred_response_length: str = "medium"  # short, medium, long

    def get_vocabulary(self, word: str) -> Optional[VocabularyItem]:
        """Get vocabulary item by word."""
        return self.vocabulary.get(word.lower())

    def add_or_update_vocabulary(
        self,
        word: str,
        translation: str,
        part_of_speech: str,
        context: str = "",
    ) -> VocabularyItem:
        """Add or update a vocabulary item."""
        word_key = word.lower()

        if word_key in self.vocabulary:
            item = self.vocabulary[word_key]
            item.record_encounter(context)
        else:
            item = VocabularyItem(
                word=word,
                translation=translation,
                part_of_speech=part_of_speech,
                language=self.target_language,
            )
            if context:
                item.contexts_seen.append(context)
            self.vocabulary[word_key] = item

        self.last_updated = datetime.now()
        return item

    def get_grammar_pattern(self, name: str) -> Optional[GrammarPattern]:
        """Get grammar pattern by name."""
        return self.grammar_patterns.get(name)

    def record_grammar_attempt(self, pattern_name: str, success: bool) -> GrammarPattern:
        """Record an attempt at using a grammar pattern."""
        if pattern_name not in self.grammar_patterns:
            # Create new pattern
            self.grammar_patterns[pattern_name] = GrammarPattern(
                name=pattern_name,
                description=f"Grammar pattern: {pattern_name}",
                category="word_order",  # Default, should be specified
            )

        pattern = self.grammar_patterns[pattern_name]
        pattern.record_attempt(success)
        self.last_updated = datetime.now()
        return pattern

    def get_weak_grammar_areas(self, threshold: float = 0.5) -> List[GrammarPattern]:
        """Get grammar patterns where learner struggles."""
        return [
            p
            for p in self.grammar_patterns.values()
            if p.mastery_score < threshold and p.attempts >= 3
        ]

    # Pronunciation methods
    def get_pronunciation_pattern(self, pattern_id: str) -> Optional[PronunciationPattern]:
        """Get pronunciation pattern by ID."""
        return self.pronunciation_patterns.get(pattern_id)

    def get_pronunciation_patterns_to_review(self) -> List[PronunciationPattern]:
        """Get pronunciation patterns that need review (spaced repetition)."""
        return [
            pattern
            for pattern in self.pronunciation_patterns.values()
            if pattern.is_due_for_review and pattern.mastery_score < 0.8
        ]

    def record_pronunciation_practice(self, pattern_id: str, quality: int) -> Optional[PronunciationPattern]:
        """
        Record a pronunciation practice attempt.

        Args:
            pattern_id: ID of the pattern practiced
            quality: 0-5 rating of performance (0=complete failure, 5=perfect)

        Returns:
            The updated pattern or None if not found
        """
        if pattern_id not in self.pronunciation_patterns:
            return None

        pattern = self.pronunciation_patterns[pattern_id]
        pattern.record_practice(quality)
        self.last_updated = datetime.now()
        return pattern

    def calculate_pronunciation_mastery(self) -> float:
        """Calculate overall pronunciation mastery score (0.0 to 1.0)."""
        if not self.pronunciation_patterns:
            return 0.0

        return sum(p.mastery_score for p in self.pronunciation_patterns.values()) / len(
            self.pronunciation_patterns
        )

    def get_vocabulary_to_review(self) -> List[VocabularyItem]:
        """Get vocabulary items that need review (spaced repetition)."""
        now = datetime.now()
        return [
            item
            for item in self.vocabulary.values()
            if item.next_review and item.next_review <= now
        ]

    def get_new_vocabulary(self, count: int = 10) -> List[VocabularyItem]:
        """Get recently encountered but not yet mastered vocabulary."""
        new_items = [
            item
            for item in self.vocabulary.values()
            if item.status in [VocabularyStatus.ENCOUNTERED, VocabularyStatus.RECOGNIZED]
        ]
        return sorted(new_items, key=lambda x: x.encounters_count, reverse=True)[:count]

    def update_confidence(self, error_count: int, total_turns: int, recent_success: bool) -> None:
        """
        Update confidence level based on conversation performance.

        Args:
            error_count: Number of errors in recent conversation
            total_turns: Total number of conversation turns
            recent_success: Whether learner successfully completed the interaction
        """
        if total_turns == 0:
            return

        error_rate = error_count / total_turns

        current_index = list(ConfidenceLevel).index(self.confidence)

        # Adjust confidence based on performance
        if error_rate < 0.1 and recent_success:
            # Very good performance - potentially increase confidence
            if self.confidence != ConfidenceLevel.VERY_HIGH:
                new_index = min(current_index + 1, len(ConfidenceLevel) - 1)
                self.confidence = list(ConfidenceLevel)[new_index]
        elif error_rate > 0.5:
            # High error rate - decrease confidence
            if self.confidence != ConfidenceLevel.VERY_LOW:
                new_index = max(current_index - 1, 0)
                self.confidence = list(ConfidenceLevel)[new_index]

        self.last_updated = datetime.now()

    def calculate_overall_mastery(self) -> float:
        """Calculate overall language mastery score (0.0 to 1.0)."""
        if not self.vocabulary:
            return 0.0

        vocab_mastery = sum(item.mastery_score for item in self.vocabulary.values()) / len(
            self.vocabulary
        )

        if self.grammar_patterns:
            grammar_mastery = sum(
                pattern.mastery_score for pattern in self.grammar_patterns.values()
            ) / len(self.grammar_patterns)
        else:
            grammar_mastery = 0.5  # Neutral if no data

        # Include pronunciation if available
        pronunciation_mastery = self.calculate_pronunciation_mastery()

        # Weight: 50% vocabulary, 30% grammar, 20% pronunciation
        return vocab_mastery * 0.5 + grammar_mastery * 0.3 + pronunciation_mastery * 0.2

    def get_learning_summary(self) -> Dict[str, Any]:
        """Get a summary of learner progress."""
        return {
            "level": self.current_cefr_level,
            "confidence": self.confidence,
            "vocabulary_size": len(self.vocabulary),
            "words mastered": sum(
                1
                for v in self.vocabulary.values()
                if v.status == VocabularyStatus.MASTERED
            ),
            "grammar patterns": len(self.grammar_patterns),
            "pronunciation patterns": len(self.pronunciation_patterns),
            "pronunciation mastery": f"{self.calculate_pronunciation_mastery():.1%}",
            "overall mastery": f"{self.calculate_overall_mastery():.1%}",
            "total conversations": self.stats.total_conversations,
            "last practiced": self.last_updated.strftime("%Y-%m-%d"),
        }

    class Config:
        arbitrary_types_allowed = True
