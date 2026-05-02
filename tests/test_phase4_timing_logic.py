"""
Tests for Phase 4 Enhanced: Teaching Timing Decision Logic.

This test suite verifies the enhanced Phase 4 implementation that includes
sophisticated timing decisions to determine WHEN to teach in conversation.
"""

import pytest
import sys
sys.path.insert(0, 'src')

from agents.grammar_curriculum import GrammarCurriculumAgent
from agents.base import AgentConfig
from models.learner import Learner, ConfidenceLevel
from models.grammar import GrammarPattern, GrammarWeakness


class TestPhase4TeachingTiming:
    """Test should_teach_now() timing decision logic."""

    @pytest.fixture
    def agent(self, learner):
        """Create a grammar curriculum agent for testing."""
        config = AgentConfig(
            name="test_timing",
            description="Test timing logic"
        )
        return GrammarCurriculumAgent(config, learner, llm_client=None)

    @pytest.fixture
    def learner(self):
        """Create a test learner."""
        learner = Learner(learner_id="test_timing")
        learner.grammar_patterns = {}
        return learner

    def test_should_teach_now_very_low_confidence_rejection(self, agent):
        """Test that VERY_LOW confidence learners are never taught, regardless of priority."""
        trigger = {"pattern": "accusative_case", "priority": 0.9}  # High priority
        context = {
            "flow_score": 0.8,
            "confidence": ConfidenceLevel.VERY_LOW,  # Cannot override
        }

        result = agent.should_teach_now(trigger, context)
        assert result is False  # Hard constraint blocks even high priority

    def test_should_teach_now_poor_flow_rejection(self, agent):
        """Test that extremely poor flow blocks teaching, regardless of priority."""
        trigger = {"pattern": "accusative_case", "priority": 0.9}
        context = {
            "flow_score": 0.2,  # Below 0.3 threshold
            "confidence": ConfidenceLevel.MODERATE,
        }

        result = agent.should_teach_now(trigger, context)
        assert result is False  # Hard constraint blocks

    def test_should_teach_now_high_priority_relaxed_thresholds(self, agent):
        """Test that high-priority triggers get relaxed flow thresholds."""
        trigger = {"pattern": "accusative_case", "priority": 0.9}
        context = {
            "flow_score": 0.4,  # Above 0.3, below 0.5
            "confidence": ConfidenceLevel.MODERATE,
            "turns_since_last_grammar": 5,  # Below frequency check
            "recent_turns": [{"learner_input": "What's next?", "error_count": 1}]  # Some errors
        }

        result = agent.should_teach_now(trigger, context)
        # High priority should allow flow 0.4+ and bypass frequency check
        # Assuming learner is receptive (asking question)
        assert result is True

    def test_should_teach_now_standard_priority_stricter_thresholds(self, agent):
        """Test that standard-priority triggers need better conditions."""
        trigger = {"pattern": "accusative_case", "priority": 0.6}
        context = {
            "flow_score": 0.4,  # Below 0.5 threshold
            "confidence": ConfidenceLevel.MODERATE,
            "turns_since_last_grammar": 15,  # Above frequency check
            "recent_turns": [{"learner_input": "Good", "error_count": 0}] * 5,
        }

        result = agent.should_teach_now(trigger, context)
        assert result is False  # Flow too low for standard priority

    def test_should_teach_now_frequency_enforcement(self, agent):
        """Test that standard-priority triggers respect teaching frequency."""
        trigger = {"pattern": "accusative_case", "priority": 0.6}
        context = {
            "flow_score": 0.7,
            "confidence": ConfidenceLevel.MODERATE,
            "turns_since_last_grammar": 3,  # Too soon
            "recent_turns": [{"learner_input": "Great!", "error_count": 0}] * 5,
        }

        result = agent.should_teach_now(trigger, context)
        assert result is False  # Frequency check blocks

    def test_should_teach_now_receptive_learner(self, agent):
        """Test that receptive learners can be taught."""
        trigger = {"pattern": "accusative_case", "priority": 0.6}
        context = {
            "flow_score": 0.7,
            "confidence": ConfidenceLevel.MODERATE,
            "turns_since_last_grammar": 15,
            "conversation": {
                "topic": "food",  # Matches accusative_case
            },
            "recent_turns": [
                {"learner_input": "How do I say X?", "error_count": 0},  # Question
                {"learner_input": "I did it!", "error_count": 0},  # Success
                {"learner_input": "Let me try", "error_count": 1},  # Trying
                {"learner_input": "Can I practice?", "error_count": 0},
                {"learner_input": "This helps", "error_count": 0},
                {"learner_input": "I'm learning", "error_count": 0},
            ],
        }

        result = agent.should_teach_now(trigger, context)
        assert result is True  # All conditions met

    def test_should_teach_now_frustrated_learner_blocked(self, agent):
        """Test that frustrated learners are not taught."""
        trigger = {"pattern": "accusative_case", "priority": 0.6}
        context = {
            "flow_score": 0.7,
            "confidence": ConfidenceLevel.MODERATE,
            "turns_since_last_grammar": 15,
            "recent_turns": [
                {"learner_input": "ok", "error_count": 5},  # Short + many errors
                {"learner_input": "hard", "error_count": 4},
                {"learner_input": "ugh", "error_count": 6},
                {"learner_input": "confusing", "error_count": 3},
                {"learner_input": "help", "error_count": 4},
            ],
        }

        result = agent.should_teach_now(trigger, context)
        assert result is False  # Frustration blocks teaching


class TestPhase4LearnerReceptiveness:
    """Test _is_learner_receptive() method."""

    @pytest.fixture
    def agent(self, learner):
        """Create a grammar curriculum agent for testing."""
        config = AgentConfig(
            name="test_receptiveness",
            description="Test learner receptiveness"
        )
        return GrammarCurriculumAgent(config, learner, llm_client=None)

    @pytest.fixture
    def learner(self):
        """Create a test learner."""
        return Learner(learner_id="test_receptiveness")

    def test_receptiveness_question_strong_positive(self, agent):
        """Test that asking questions indicates strong receptiveness."""
        context = {
            "recent_turns": [
                {"learner_input": "What about X?", "error_count": 1},
                {"learner_input": "How do I say this?", "error_count": 0},
            ]
        }

        result = agent._is_learner_receptive(context)
        assert result is True  # Questions indicate engagement

    def test_receptiveness_no_errors_positive(self, agent):
        """Test that error-free success indicates receptiveness."""
        context = {
            "recent_turns": [
                {"learner_input": "I did it perfectly", "error_count": 0},
                {"learner_input": "This makes sense", "error_count": 0},
            ] * 3,
        }

        result = agent._is_learner_receptive(context)
        assert result is True  # No errors = ready for new material

    def test_receptiveness_frustration_blocks(self, agent):
        """Test that frustration signals block teaching."""
        context = {
            "recent_turns": [
                {"learner_input": "ugh", "error_count": 4},  # Short
                {"learner_input": "ok", "error_count": 5},  # Very short
                {"learner_input": "hard", "error_count": 6},  # Short
                {"learner_input": "confusing", "error_count": 4},
                {"learner_input": "help", "error_count": 5},
            ],
        }

        result = agent._is_learner_receptive(context)
        assert result is False  # Frustration overrides

    def test_receptiveness_attempts_encouraging(self, agent):
        """Test that grammar attempts despite errors show engagement."""
        context = {
            "recent_turns": [
                {"learner_input": "I tried the new pattern", "error_count": 1},
                {"learner_input": "Let me practice again", "error_count": 2},
                {"learner_input": "Almost got it", "error_count": 1},
            ],
        }

        result = agent._is_learner_receptive(context)
        assert result is True  # Trying despite errors

    def test_receptiveness_insufficient_data(self, agent):
        """Test that insufficient data assumes receptiveness."""
        context = {
            "recent_turns": [
                {"learner_input": "Hello", "error_count": 0},
            ]  # Only 1 turn
        }

        result = agent._is_learner_receptive(context)
        assert result is True  # Not enough data, assume receptive


class TestPhase4NaturalIntegration:
    """Test _fits_conversation_naturally() method."""

    @pytest.fixture
    def agent(self, learner):
        """Create a grammar curriculum agent for testing."""
        config = AgentConfig(
            name="test_natural_fit",
            description="Test natural conversation integration"
        )
        return GrammarCurriculumAgent(config, learner, llm_client=None)

    @pytest.fixture
    def learner(self):
        """Create a test learner."""
        learner = Learner(learner_id="test_natural_fit")
        learner.grammar_patterns = {}
        return learner

    def test_natural_fit_high_priority_bypass(self, agent):
        """Test that high-priority triggers bypass natural fit check."""
        trigger = {
            "pattern": "accusative_case",
            "priority": 0.8  # High priority
        }
        context = {
            "conversation": {
                "topic": "unrelated_topic"  # Doesn't match pattern
            }
        }

        result = agent._fits_conversation_naturally(trigger, context)
        assert result is True  # High priority bypasses check

    def test_natural_fit_topic_match(self, agent):
        """Test that topic matching enables teaching."""
        trigger = {
            "pattern": "accusative_case",  # Used for "food" topic
            "priority": 0.6
        }
        context = {
            "conversation": {
                "topic": "food"  # Matches accusative_case
            }
        }

        result = agent._fits_conversation_naturally(trigger, context)
        assert result is True  # Natural fit!

    def test_natural_fit_no_topic_no_match(self, agent):
        """Test that standard priority needs topic or related patterns."""
        trigger = {
            "pattern": "dative_case",  # Not in basic topics
            "priority": 0.6
        }
        context = {
            "conversation": {
                "topic": "greetings"  # Doesn't use dative
            }
        }

        result = agent._fits_conversation_naturally(trigger, context)
        assert result is False  # No natural fit


class TestPhase4RuleBasedIntegration:
    """Test Phase 4 integration with rule-based decision making."""

    @pytest.fixture
    def agent(self, learner):
        """Create a grammar curriculum agent for testing."""
        config = AgentConfig(
            name="test_integration",
            description="Test Phase 4 integration"
        )
        return GrammarCurriculumAgent(config, learner, llm_client=None)

    @pytest.fixture
    def learner(self):
        """Create a test learner."""
        learner = Learner(learner_id="test_integration")
        learner.grammar_patterns = {}
        return learner

    def test_rule_based_timing_evaluation(self, agent):
        """Test that rule-based decisions use timing evaluation."""
        # Create context that should block teaching
        context = {
            "learner_state": {
                "cefr_level": "A1",
                "confidence": ConfidenceLevel.MODERATE,
                "recent_errors": [],
                "mastered_patterns": {},
                "weaknesses": [],
            },
            "conversation": {
                "topic": "family",
                "flow_score": 0.2,  # Too poor
                "recent_input": "Ich habe...",
                "turns_since_last_grammar": 20,
            },
            "recent_turns": [
                {"learner_input": "I'm struggling", "error_count": 4},
                {"learner_input": "This is hard", "error_count": 3},
            ] * 3,
        }

        decision = agent._rule_based_teaching_decision(context)

        # Should return "wait" because flow is too poor
        assert decision["action"] == "wait"
        assert "timing" in decision["reasoning"].lower()

    def test_rule_based_teach_when_receptive(self, agent):
        """Test that rule-based decisions teach when learner is receptive."""
        # Add a mastered pattern to create a prerequisite_ready trigger
        mastered_pattern = GrammarPattern(
            name="definite_articles_nominative",
            description="Test",
            category=GrammarWeakness.ARTICLE_USAGE
        )
        for _ in range(8):
            mastered_pattern.record_attempt(success=True)
        agent.learner.grammar_patterns["definite_articles_nominative"] = mastered_pattern

        context = {
            "learner_state": {
                "cefr_level": "A1",
                "confidence": ConfidenceLevel.MODERATE,
                "recent_errors": [],
                "mastered_patterns": {"definite_articles_nominative": {}},
                "weaknesses": [],
            },
            "conversation": {
                "topic": "family",  # Uses definite_articles_nominative
                "flow_score": 0.7,
                "recent_input": "I want to eat",
                "turns_since_last_grammar": 15,
            },
            "recent_turns": [
                {"learner_input": "What's next?", "error_count": 0},
                {"learner_input": "This is fun!", "error_count": 0},
                {"learner_input": "Great practice", "error_count": 0},
                {"learner_input": "I'm learning fast", "error_count": 0},
                {"learner_input": "Can we continue?", "error_count": 0},
            ],
        }

        decision = agent._rule_based_teaching_decision(context)

        # Should teach because learner is receptive and topic matches
        assert decision["action"] in ["introduce_pattern", "review_pattern", "reinforce_pattern"]
        assert decision["pattern"] is not None


class TestPhase4TriggerTypeMapping:
    """Test that new Phase 4 trigger types map to correct actions."""

    @pytest.fixture
    def agent(self, learner):
        """Create a grammar curriculum agent for testing."""
        config = AgentConfig(name="test_mapping", description="Test trigger mapping")
        return GrammarCurriculumAgent(config, learner, llm_client=None)

    @pytest.fixture
    def learner(self):
        """Create a test learner."""
        return Learner(learner_id="test_mapping")

    def test_topic_introduction_mapping(self, agent):
        """Test that topic_relevant_introduction maps to introduce_pattern."""
        action = agent._map_trigger_type_to_action("topic_relevant_introduction")
        assert action == "introduce_pattern"

    def test_topic_review_mapping(self, agent):
        """Test that topic_relevant_review maps to review_pattern."""
        action = agent._map_trigger_type_to_action("topic_relevant_review")
        assert action == "review_pattern"

    def test_topic_fallback_mapping(self, agent):
        """Test that generic topic_relevant defaults to introduce_pattern."""
        action = agent._map_trigger_type_to_action("topic_relevant")
        assert action == "introduce_pattern"

    def test_existing_trigger_mappings(self, agent):
        """Test that existing trigger types still map correctly."""
        assert agent._map_trigger_type_to_action("review_due") == "review_pattern"
        assert agent._map_trigger_type_to_action("recurring_error") == "reinforce_pattern"
        assert agent._map_trigger_type_to_action("prerequisite_ready") == "introduce_pattern"

    def test_unknown_trigger_maps_to_wait(self, agent):
        """Test that unknown trigger types map to wait."""
        action = agent._map_trigger_type_to_action("unknown_trigger")
        assert action == "wait"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])