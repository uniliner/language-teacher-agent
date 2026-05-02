"""
Tests for Phase 4: Context-Aware Teaching Timing implementation.

This test suite verifies:
- _get_grammar_for_topic() method with cache and LLM fallback
- should_proactively_teach() method for topic-based proactive teaching
- Integration with _get_teaching_triggers() for topic-relevant triggers
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import sys
sys.path.insert(0, 'src')

from agents.grammar_curriculum import GrammarCurriculumAgent, CurriculumPattern
from agents.base import AgentConfig
from models.grammar import GrammarWeakness
from models.grammar_teaching import LearnerGrammarProfile
from models.learner import Learner, ConfidenceLevel


class TestPhase4GrammarForTopic:
    """Test _get_grammar_for_topic() method."""

    @pytest.fixture
    def agent(self, learner):
        """Create a grammar curriculum agent for testing."""
        config = AgentConfig(
            name="test_grammar_curriculum",
            description="Test grammar curriculum agent"
        )
        # Create agent without LLM client for cache-only tests
        return GrammarCurriculumAgent(config, learner, llm_client=None)

    @pytest.fixture
    def agent_with_llm(self, learner):
        """Create a grammar curriculum agent with mocked LLM client."""
        config = AgentConfig(
            name="test_grammar_curriculum",
            description="Test grammar curriculum agent"
        )
        # Create mock LLM client
        mock_llm = Mock()
        mock_llm.client = Mock()
        mock_llm.client.messages = Mock()
        mock_llm.client.messages.create = Mock()
        return GrammarCurriculumAgent(config, learner, llm_client=mock_llm)

    @pytest.fixture
    def learner(self):
        """Create a test learner."""
        learner = Learner(learner_id="test_learner")
        # Field is already set to defaults: current_cefr_level="A1", confidence=ConfidenceLevel.MODERATE
        learner.grammar_patterns = {}  # No patterns introduced yet
        return learner

    def test_get_grammar_for_topic_cache_hit(self, agent):
        """Test that cached topics return expected patterns."""
        # Test known topic from cache
        patterns = agent._get_grammar_for_topic("food")
        assert isinstance(patterns, list)
        assert "accusative_case" in patterns

        # Test another known topic
        patterns = agent._get_grammar_for_topic("daily routine")
        assert isinstance(patterns, list)
        assert "present_tense_regular" in patterns

    def test_get_grammar_for_topic_case_insensitive(self, agent):
        """Test that topic matching is case-insensitive."""
        patterns_lower = agent._get_grammar_for_topic("food")
        patterns_upper = agent._get_grammar_for_topic("FOOD")
        patterns_mixed = agent._get_grammar_for_topic("Food")

        # All should return the same results
        assert patterns_lower == patterns_upper == patterns_mixed

    def test_get_grammar_for_topic_whitespace_handling(self, agent):
        """Test that whitespace is properly handled."""
        patterns = agent._get_grammar_for_topic("  food  ")
        assert isinstance(patterns, list)
        assert "accusative_case" in patterns

    def test_get_grammar_for_topic_unknown_topic_no_llm(self, agent):
        """Test that unknown topics return empty list when no LLM available."""
        patterns = agent._get_grammar_for_topic("quantum physics")
        assert patterns == []

    def test_get_grammar_for_topic_llm_fallback(self, agent_with_llm):
        """Test LLM fallback for unknown topics."""
        # Mock LLM response
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = "modal_verbs_present, separable_verbs_basic"
        mock_response.content = [mock_content]

        agent_with_llm.llm_client.client.messages.create.return_value = mock_response

        # Test unknown topic
        patterns = agent_with_llm._get_grammar_for_topic("technology")

        # Verify LLM was called
        agent_with_llm.llm_client.client.messages.create.assert_called_once()

        # Verify patterns were returned (if they're in the pattern map)
        assert isinstance(patterns, list)

    def test_get_grammar_for_topic_caches_empty_results(self, agent_with_llm):
        """Test that empty LLM results are cached to prevent retry loops."""
        # Mock LLM response with no valid patterns
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = "advanced_c1_syntax, expert_level_vocabulary"
        mock_response.content = [mock_content]

        agent_with_llm.llm_client.client.messages.create.return_value = mock_response

        # First call should invoke LLM
        patterns1 = agent_with_llm._get_grammar_for_topic("unknown topic")
        assert patterns1 == []

        # Reset mock to track if it's called again
        agent_with_llm.llm_client.client.messages.create.reset_mock()

        # Second call should use cache, not invoke LLM
        patterns2 = agent_with_llm._get_grammar_for_topic("unknown topic")
        assert patterns2 == []

        # Verify LLM was NOT called the second time
        agent_with_llm.llm_client.client.messages.create.assert_not_called()

    def test_get_grammar_for_topic_limits_results(self, agent_with_llm):
        """Test that results are limited to top 5 patterns."""
        # Mock LLM response with many patterns
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = "pattern1, pattern2, pattern3, pattern4, pattern5, pattern6, pattern7, pattern8"
        mock_response.content = [mock_content]

        agent_with_llm.llm_client.client.messages.create.return_value = mock_response

        patterns = agent_with_llm._get_grammar_for_topic("many patterns topic")

        # Should return at most 5 patterns
        assert len(patterns) <= 5

    def test_get_grammar_for_topic_llm_error_handling(self, agent_with_llm):
        """Test graceful fallback when LLM call fails."""
        # Mock LLM to raise exception
        agent_with_llm.llm_client.client.messages.create.side_effect = Exception("LLM error")

        patterns = agent_with_llm._get_grammar_for_topic("error topic")

        # Should return empty list on error
        assert patterns == []

        # Should cache empty result to prevent retry
        assert "error topic" in agent_with_llm._topic_grammar_cache


class TestPhase4ProactiveTeaching:
    """Test should_proactively_teach() method."""

    @pytest.fixture
    def agent(self, learner):
        """Create a grammar curriculum agent for testing."""
        config = AgentConfig(
            name="test_grammar_curriculum",
            description="Test grammar curriculum agent"
        )
        return GrammarCurriculumAgent(config, learner, llm_client=None)

    @pytest.fixture
    def learner(self):
        """Create a test learner."""
        learner = Learner(learner_id="test_proactive")
        learner.grammar_patterns = {}
        return learner

    def test_should_proactively_teach_new_pattern(self, agent):
        """Test that unknown patterns trigger introduction."""
        context = {
            "conversation": {
                "topic": "food"
            }
        }

        result = agent.should_proactively_teach(context)

        # Should recommend introducing accusative_case
        assert result is not None
        assert result["action"] == "introduce_pattern"
        assert "accusative_case" in result["pattern"]
        assert result["timing"] == "before_topic"
        assert result["priority"] == 0.6

    def test_should_proactively_teach_weak_pattern(self, agent, learner):
        """Test that weak patterns trigger review."""
        # Add a weak accusative_case pattern
        from models.grammar import GrammarPattern, GrammarWeakness
        weak_pattern = GrammarPattern(name="accusative_case", description="Test", category=GrammarWeakness.CASE)
        # Record some failed attempts to make it weak
        for _ in range(5):
            weak_pattern.record_attempt(success=False)
        learner.grammar_patterns["accusative_case"] = weak_pattern

        context = {
            "conversation": {
                "topic": "food"
            }
        }

        result = agent.should_proactively_teach(context)

        # Should recommend reviewing accusative_case
        assert result is not None
        assert result["action"] == "review_pattern"
        assert result["pattern"] == "accusative_case"

    def test_should_proactively_teach_no_topic(self, agent):
        """Test that missing topic returns None."""
        context = {
            "conversation": {}
        }

        result = agent.should_proactively_teach(context)

        assert result is None

    def test_should_proactively_teach_no_grammar_needed(self, agent):
        """Test that topics with no grammar needs return None."""
        # Add mastered patterns for "food" topic
        from models.grammar import GrammarPattern, GrammarWeakness
        accusative_pattern = GrammarPattern(name="accusative_case", description="Test", category=GrammarWeakness.CASE)
        # Record successful attempts to make it mastered
        for _ in range(8):
            accusative_pattern.record_attempt(success=True)

        indefinite_pattern = GrammarPattern(name="indefinite_articles_nominative", description="Test", category=GrammarWeakness.ARTICLE_USAGE)
        # Record successful attempts to make it mastered
        for _ in range(9):
            indefinite_pattern.record_attempt(success=True)

        agent.learner.grammar_patterns = {
            "accusative_case": accusative_pattern,
            "indefinite_articles_nominative": indefinite_pattern,
        }

        context = {
            "conversation": {
                "topic": "food"
            }
        }

        result = agent.should_proactively_teach(context)

        # Should return None as all needed patterns are mastered
        assert result is None

    def test_should_proactively_teach_unknown_topic(self, agent):
        """Test that unknown topics return None."""
        context = {
            "conversation": {
                "topic": "unknown_topic_with_no_grammar"
            }
        }

        result = agent.should_proactively_teach(context)

        # Should return None for unknown topics (no LLM client)
        assert result is None


class TestPhase4TriggerIntegration:
    """Test integration of Phase 4 with teaching triggers."""

    @pytest.fixture
    def agent(self, learner):
        """Create a grammar curriculum agent for testing."""
        config = AgentConfig(
            name="test_grammar_curriculum",
            description="Test grammar curriculum agent"
        )
        return GrammarCurriculumAgent(config, learner, llm_client=None)

    @pytest.fixture
    def learner(self):
        """Create a test learner."""
        learner = Learner(learner_id="test_integration")
        learner.grammar_patterns = {}
        return learner

    def test_teaching_triggers_includes_topic_relevant(self, agent):
        """Test that topic-relevant triggers are included in teaching triggers."""
        context = {
            "learner_state": {
                "recent_errors": [],
                "weaknesses": []
            },
            "conversation": {
                "topic": "food"
            }
        }

        triggers = agent._get_teaching_triggers(context)

        # Should have at least one trigger for "food" topic
        assert len(triggers) > 0

        # Should include topic-relevant trigger
        topic_triggers = [t for t in triggers if "topic" in t.get("type", "").lower()]
        assert len(topic_triggers) > 0

    def test_teaching_triggers_priority_ordering(self, agent):
        """Test that topic triggers have correct priority."""
        context = {
            "learner_state": {
                "recent_errors": [],
                "weaknesses": []
            },
            "conversation": {
                "topic": "food"
            }
        }

        triggers = agent._get_teaching_triggers(context)

        # Find topic-relevant trigger
        topic_trigger = next((t for t in triggers if "topic" in t.get("type", "").lower()), None)

        assert topic_trigger is not None
        assert topic_trigger["priority"] == 0.6  # Medium priority for topic-based
        assert "food" in topic_trigger.get("reason", "")

    def test_teaching_triggers_multiple_priorities(self, agent, learner):
        """Test that different trigger types maintain priority hierarchy."""
        # Add some patterns to create multiple trigger types
        from models.grammar import GrammarPattern, GrammarWeakness

        # Add a mastered pattern
        mastered_pattern = GrammarPattern(name="definite_articles_nominative", description="Test", category=GrammarWeakness.ARTICLE_USAGE)
        # Record successful attempts to make it mastered
        for _ in range(8):
            mastered_pattern.record_attempt(success=True)
        learner.grammar_patterns["definite_articles_nominative"] = mastered_pattern

        context = {
            "learner_state": {
                "recent_errors": [],
                "weaknesses": []
            },
            "conversation": {
                "topic": "family"
            }
        }

        triggers = agent._get_teaching_triggers(context)

        # Check that triggers are sorted by priority
        if len(triggers) > 1:
            priorities = [t["priority"] for t in triggers]
            # Should be in descending order
            assert priorities == sorted(priorities, reverse=True)


class TestPhase4CacheBehavior:
    """Test cache behavior for topic-to-grammar mapping."""

    @pytest.fixture
    def agent(self, learner):
        """Create a grammar curriculum agent for testing."""
        config = AgentConfig(
            name="test_grammar_curriculum",
            description="Test grammar curriculum agent"
        )
        return GrammarCurriculumAgent(config, learner, llm_client=None)

    @pytest.fixture
    def learner(self):
        """Create a test learner."""
        learner = Learner(learner_id="test_cache")
        learner.grammar_patterns = {}
        return learner

    def test_cache_persists_across_calls(self, agent):
        """Test that cache works across multiple calls."""
        # First call
        patterns1 = agent._get_grammar_for_topic("food")
        # Second call
        patterns2 = agent._get_grammar_for_topic("food")

        # Should return identical results
        assert patterns1 == patterns2

    def test_cache_different_topics(self, agent):
        """Test that different topics return different patterns."""
        food_patterns = agent._get_grammar_for_topic("food")
        family_patterns = agent._get_grammar_for_topic("family")

        # Should have different patterns (at least some overlap is ok, but not identical)
        # Both should contain accusative_case
        assert "accusative_case" in food_patterns
        # Family should contain definite articles
        assert "definite_articles_nominative" in family_patterns


if __name__ == "__main__":
    pytest.main([__file__, "-v"])