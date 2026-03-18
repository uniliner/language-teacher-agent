"""
Tests for learner state models.
"""

import pytest
from datetime import datetime

from src.models.learner import Learner, ConfidenceLevel
from src.models.vocabulary import VocabularyItem, VocabularyStatus
from src.models.grammar import GrammarPattern, GrammarWeakness


class TestVocabularyItem:
    """Test vocabulary item model."""

    def test_creation(self):
        """Test creating a vocabulary item."""
        item = VocabularyItem(
            word="Hund",
            translation="dog",
            part_of_speech="noun"
        )

        assert item.word == "Hund"
        assert item.translation == "dog"
        assert item.status == VocabularyStatus.NEW
        assert item.mastery_score == 0.0

    def test_encounter_tracking(self):
        """Test recording encounters."""
        item = VocabularyItem(
            word="Katze",
            translation="cat",
            part_of_speech="noun"
        )

        item.record_encounter("Ich habe eine Katze")

        assert item.encounters_count == 1
        assert item.last_seen is not None

    def test_production_tracking(self):
        """Test recording production attempts."""
        item = VocabularyItem(
            word="Haus",
            translation="house",
            part_of_speech="noun"
        )

        item.record_production(correct=True)
        item.record_production(correct=False)
        item.record_production(correct=True)

        assert item.correct_productions == 2
        assert item.incorrect_productions == 1

    def test_spaced_repetition(self):
        """Test spaced repetition algorithm."""
        item = VocabularyItem(
            word="Baum",
            translation="tree",
            part_of_speech="noun"
        )

        # First successful review
        item.update_spaced_repetition(quality=5)
        assert item.interval == 1
        assert item.next_review is not None

    def test_mastery_progression(self):
        """Test mastery status progression."""
        item = VocabularyItem(
            word="Auto",
            translation="car",
            part_of_speech="noun"
        )

        # Start at new
        assert item.status == VocabularyStatus.NEW

        # After encounters
        for _ in range(5):
            item.record_encounter("context")
        assert item.status == VocabularyStatus.ENCOUNTERED

        # After successful productions
        for _ in range(10):
            item.record_production(correct=True)
        assert item.status in [VocabularyStatus.PRODUCTION, VocabularyStatus.RECOGNIZED]


class TestGrammarPattern:
    """Test grammar pattern model."""

    def test_creation(self):
        """Test creating a grammar pattern."""
        pattern = GrammarPattern(
            name="verb_position",
            description="Verb must be second position",
            category=GrammarWeakness.WORD_ORDER
        )

        assert pattern.name == "verb_position"
        assert pattern.attempts == 0
        assert pattern.mastery_score == 0.0

    def test_attempt_tracking(self):
        """Test recording attempts."""
        pattern = GrammarPattern(
            name="case_system",
            description="German case system",
            category=GrammarWeakness.CASE
        )

        pattern.record_attempt(success=True)
        pattern.record_attempt(success=False)
        pattern.record_attempt(success=True)

        assert pattern.attempts == 3
        assert pattern.successes == 2
        assert pattern.errors == 1

    def test_error_rate(self):
        """Test error rate calculation."""
        pattern = GrammarPattern(
            name="gender",
            description="Article gender agreement",
            category=GrammarWeakness.GENDER
        )

        for _ in range(3):
            pattern.record_attempt(success=False)
        for _ in range(7):
            pattern.record_attempt(success=True)

        assert pattern.error_rate == 0.3

    def test_needs_review(self):
        """Test review determination."""
        pattern = GrammarPattern(
            name="adjective_ending",
            description="Adjective ending after der-word",
            category=GrammarWeakness.ADJECTIVE_ENDING
        )

        # Low attempt count should trigger review
        assert pattern.needs_review is True

        # After successful attempts
        for _ in range(10):
            pattern.record_attempt(success=True)
        assert pattern.needs_review is False

        # Recent errors should trigger review
        pattern.record_attempt(success=False)
        assert pattern.needs_review is True


class TestLearner:
    """Test learner model."""

    def test_creation(self):
        """Test creating a learner."""
        learner = Learner(
            learner_id="test_learner",
            target_language="german",
            current_cefr_level="A1"
        )

        assert learner.learner_id == "test_learner"
        assert learner.target_language == "german"
        assert len(learner.vocabulary) == 0
        assert len(learner.grammar_patterns) == 0

    def test_vocabulary_management(self):
        """Test adding and retrieving vocabulary."""
        learner = Learner(learner_id="test_learner")

        # Add vocabulary
        item = learner.add_or_update_vocabulary(
            word="Tisch",
            translation="table",
            part_of_speech="noun"
        )

        assert item.word == "Tisch"
        assert "tisch" in learner.vocabulary

        # Retrieve vocabulary
        retrieved = learner.get_vocabulary("Tisch")
        assert retrieved is not None
        assert retrieved.word == "Tisch"

    def test_grammar_tracking(self):
        """Test grammar pattern tracking."""
        learner = Learner(learner_id="test_learner")

        # Record attempts
        learner.record_grammar_attempt("word_order", success=True)
        learner.record_grammar_attempt("word_order", success=False)

        assert "word_order" in learner.grammar_patterns
        pattern = learner.grammar_patterns["word_order"]
        assert pattern.attempts == 2

    def test_confidence_update(self):
        """Test confidence level updates."""
        learner = Learner(
            learner_id="test_learner",
            confidence=ConfidenceLevel.MODERATE
        )

        # Good performance should increase confidence
        learner.update_confidence(error_count=1, total_turns=10, recent_success=True)
        # Should stay or increase
        assert list(ConfidenceLevel).index(learner.confidence) >= 2

    def test_weak_grammar_areas(self):
        """Test identifying weak grammar areas."""
        learner = Learner(learner_id="test_learner")

        # Add some patterns with different performance
        for _ in range(10):
            learner.record_grammar_attempt("strong_pattern", success=True)
        for i in range(10):
            learner.record_grammar_attempt("weak_pattern", success=(i < 4))

        weak = learner.get_weak_grammar_areas(threshold=0.7)

        # weak_pattern should be in weak areas
        weak_names = [p.name for p in weak]
        assert "weak_pattern" in weak_names

    def test_learning_summary(self):
        """Test learning summary generation."""
        learner = Learner(
            learner_id="test_learner",
            current_cefr_level="A1",
            confidence=ConfidenceLevel.MODERATE
        )

        # Add some vocabulary
        learner.add_or_update_vocabulary("Wort1", "word1", "noun")
        learner.add_or_update_vocabulary("Wort2", "word2", "verb")

        summary = learner.get_learning_summary()

        assert "level" in summary
        assert summary["level"] == "A1"
        assert summary["vocabulary_size"] == 2
