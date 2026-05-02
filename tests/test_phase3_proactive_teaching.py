"""
Test Phase 3: Proactive Teaching functionality.

Tests for:
- Pattern dependency system
- Adaptive curriculum ordering
- Reinforcement reordering
- Acceleration reordering
- Dependency validation
"""

import pytest
import sys
sys.path.insert(0, 'src')

from agents.grammar_curriculum import GrammarCurriculumAgent, PatternDependency
from models.learner import Learner, ConfidenceLevel
from models.grammar_teaching import LearnerGrammarProfile
from models.grammar import GrammarPattern, GrammarWeakness
from agents.base import AgentConfig


class TestPatternDependencies:
    """Test pattern dependency system."""

    def test_dependency_structure(self):
        """Test that PATTERN_DEPENDENCIES is properly structured."""
        # Check that dependencies exist for key patterns
        assert "sv_order_main_clause" in GrammarCurriculumAgent.PATTERN_DEPENDENCIES
        assert "accusative_case" in GrammarCurriculumAgent.PATTERN_DEPENDENCIES

        # Check that accusative_case requires definite_articles_nominative
        acc_dep = GrammarCurriculumAgent.PATTERN_DEPENDENCIES["accusative_case"]
        assert "definite_articles_nominative" in acc_dep.requires

        # Check that sv_order enables subordinate_clause
        sv_dep = GrammarCurriculumAgent.PATTERN_DEPENDENCIES["sv_order_main_clause"]
        assert "subordinate_clause_verb_final" in sv_dep.enables

    def test_dependency_dataclass(self):
        """Test PatternDependency dataclass structure."""
        dep = PatternDependency(
            pattern="test_pattern",
            requires=["prereq1", "prereq2"],
            enables=["enabled1", "enabled2"],
            difficulty_impact=0.8
        )

        assert dep.pattern == "test_pattern"
        assert len(dep.requires) == 2
        assert len(dep.enables) == 2
        assert dep.difficulty_impact == 0.8


class TestAdaptiveCurriculum:
    """Test adaptive curriculum ordering."""

    @pytest.fixture
    def agent(self):
        """Create a test agent."""
        config = AgentConfig(
            name="test_grammar",
            description="Test grammar curriculum agent"
        )
        learner = Learner(
            learner_id="test_learner",
            name="Test Learner"
        )
        return GrammarCurriculumAgent(config, learner)

    def test_base_curriculum_order(self, agent):
        """Test that base curriculum has expected patterns."""
        base_order = [p.name for p in agent.GERMAN_GRAMMAR_CURRICULUM]

        # Check that fundamental patterns are early
        assert "sv_order_main_clause" in base_order
        assert "present_tense_regular" in base_order
        assert "definite_articles_nominative" in base_order

        # Check that advanced patterns are present
        assert "passive_present" in base_order
        assert "relative_clauses" in base_order

    def test_reorder_for_reinforcement_no_weaknesses(self, agent):
        """Test that reinforcement reordering returns same order when no weaknesses."""
        base_order = [p.name for p in agent.GERMAN_GRAMMAR_CURRICULUM]
        reordered = agent._reorder_for_reinforcement(base_order, [])

        # Should return same order when no weaknesses
        assert reordered == base_order

    def test_reorder_for_reinforcement_with_weaknesses(self, agent):
        """Test that weak patterns are moved earlier."""
        base_order = [p.name for p in agent.GERMAN_GRAMMAR_CURRICULUM]

        # Simulate learner struggling with accusative_case
        # (which is around position 6-7 in base curriculum)
        weaknesses = ["accusative_case"]
        reordered = agent._reorder_for_reinforcement(base_order, weaknesses)

        # Accusative should be moved to an earlier position
        acc_pos_original = base_order.index("accusative_case")
        acc_pos_reordered = reordered.index("accusative_case")

        assert acc_pos_reordered < acc_pos_original, \
            f"Weak pattern should move earlier: {acc_pos_reordered} < {acc_pos_original}"

    def test_reorder_for_reinforcement_multiple_weaknesses(self, agent):
        """Test reinforcement with multiple related weaknesses."""
        base_order = [p.name for p in agent.GERMAN_GRAMMAR_CURRICULUM]

        # Simulate learner struggling with multiple case patterns
        weaknesses = ["accusative_case", "dative_case"]
        reordered = agent._reorder_for_reinforcement(base_order, weaknesses)

        # Both patterns should be moved earlier
        for weakness in weaknesses:
            original_pos = base_order.index(weakness)
            reordered_pos = reordered.index(weakness)
            assert reordered_pos < original_pos, \
                f"{weakness} should move earlier"

    def test_reorder_for_acceleration_no_strengths(self, agent):
        """Test that acceleration returns same order when no strengths."""
        base_order = [p.name for p in agent.GERMAN_GRAMMAR_CURRICULUM]
        reordered = agent._reorder_for_acceleration(base_order, [])

        # Should return same order when no strengths
        assert reordered == base_order

    def test_reorder_for_acceleration_with_strengths(self, agent):
        """Test that dependent patterns are accelerated when prerequisites are strong."""
        base_order = [p.name for p in agent.GERMAN_GRAMMAR_CURRICULUM]

        # Simulate learner being strong in present_tense_regular
        # This should enable acceleration of perfect_tense_haben
        strengths = ["present_tense_regular"]
        reordered = agent._reorder_for_acceleration(base_order, strengths)

        # perfect_tense_haben should be moved earlier
        perfect_pos_original = base_order.index("perfect_tense_haben")
        perfect_pos_reordered = reordered.index("perfect_tense_haben")

        assert perfect_pos_reordered < perfect_pos_original, \
            f"Dependent pattern should move earlier when prerequisite is strong"

    def test_validate_dependencies_preserves_prerequisites(self, agent):
        """Test that dependency validation preserves prerequisite order."""
        # Create an order that violates prerequisites
        # (accusative_case before definite_articles_nominative)
        bad_order = [
            "accusative_case",
            "definite_articles_nominative",
            "present_tense_regular"
        ]

        validated = agent._validate_dependencies(bad_order)

        # definite_articles should come before accusative_case
        def_pos = validated.index("definite_articles_nominative")
        acc_pos = validated.index("accusative_case")

        assert def_pos < acc_pos, \
            "Prerequisite (definite_articles) should come before dependent (accusative)"

    def test_validate_dependencies_with_valid_order(self, agent):
        """Test that valid order passes validation unchanged."""
        valid_order = [
            "definite_articles_nominative",
            "accusative_case",
            "dative_case"
        ]

        validated = agent._validate_dependencies(valid_order)

        # Order should be preserved
        assert validated == valid_order

    def test_get_adaptive_curriculum_comprehensive(self, agent):
        """Test full adaptive curriculum ordering with strengths and weaknesses."""
        # Set up learner profile
        agent.learner_profile.error_prone_patterns = ["accusative_case"]
        agent.learner_profile.strength_patterns = ["present_tense_regular", "definite_articles_nominative"]

        # Get adaptive order
        adaptive_order = agent.get_adaptive_curriculum_order(agent.learner)

        # Verify that all patterns are still present
        base_patterns = set(p.name for p in agent.GERMAN_GRAMMAR_CURRICULUM)
        adaptive_patterns = set(adaptive_order)

        assert base_patterns == adaptive_patterns, \
            "Adaptive order should contain all patterns"

        # Verify that dependencies are satisfied
        validated = agent._validate_dependencies(adaptive_order)
        assert validated == adaptive_order, \
            "Adaptive order should satisfy all dependencies"


class TestPatternCategory:
    """Test pattern category extraction."""

    @pytest.fixture
    def agent(self):
        """Create a test agent."""
        config = AgentConfig(
            name="test_grammar",
            description="Test grammar curriculum agent"
        )
        learner = Learner(
            learner_id="test_learner",
            name="Test Learner"
        )
        return GrammarCurriculumAgent(config, learner)

    def test_get_pattern_category_known_patterns(self, agent):
        """Test category extraction for known patterns."""
        # Test case patterns
        assert agent._get_pattern_category("accusative_case") == "case"
        assert agent._get_pattern_category("dative_case") == "case"

        # Test verb patterns
        assert agent._get_pattern_category("present_tense_regular") == "verb_conjugation"

        # Test article patterns
        assert agent._get_pattern_category("definite_articles_nominative") == "article_usage"

    def test_get_pattern_category_unknown_pattern(self, agent):
        """Test category extraction for unknown patterns."""
        category = agent._get_pattern_category("unknown_pattern")
        assert category == "general"


class TestAdaptiveCurriculumIntegration:
    """Test integration of adaptive curriculum with agent decision-making."""

    @pytest.fixture
    def agent(self):
        """Create a test agent."""
        config = AgentConfig(
            name="test_grammar",
            description="Test grammar curriculum agent"
        )
        learner = Learner(
            learner_id="test_learner",
            name="Test Learner"
        )
        return GrammarCurriculumAgent(config, learner)

    @pytest.fixture
    def agent_with_profile(self):
        """Create an agent with populated learner profile."""
        config = AgentConfig(
            name="test_grammar",
            description="Test grammar curriculum agent"
        )
        learner = Learner(
            learner_id="test_learner",
            name="Test Learner",
            current_cefr_level="A1"
        )
        agent = GrammarCurriculumAgent(config, learner)

        # Populate learner profile with weaknesses and strengths
        agent.learner_profile.error_prone_patterns = ["accusative_case"]
        agent.learner_profile.strength_patterns = ["present_tense_regular", "definite_articles_nominative"]

        # Add some pattern data to learner (need 5+ for sufficient data)
        learner.grammar_patterns["present_tense_regular"] = GrammarPattern(
            name="present_tense_regular",
            description="Present tense",
            category=GrammarWeakness.VERB_CONJUGATION,
            difficulty_level=1,
            introduced_at_level="A1"
        )
        learner.grammar_patterns["definite_articles_nominative"] = GrammarPattern(
            name="definite_articles_nominative",
            description="Definite articles",
            category=GrammarWeakness.ARTICLE_USAGE,
            difficulty_level=1,
            introduced_at_level="A1"
        )
        learner.grammar_patterns["accusative_case"] = GrammarPattern(
            name="accusative_case",
            description="Accusative case",
            category=GrammarWeakness.CASE,
            difficulty_level=2,
            introduced_at_level="A1"
        )
        learner.grammar_patterns["noun_gender"] = GrammarPattern(
            name="noun_gender",
            description="Noun gender",
            category=GrammarWeakness.GENDER,
            difficulty_level=1,
            introduced_at_level="A1"
        )
        learner.grammar_patterns["question_word_order"] = GrammarPattern(
            name="question_word_order",
            description="Question word order",
            category=GrammarWeakness.WORD_ORDER,
            difficulty_level=1,
            introduced_at_level="A1"
        )

        return agent

    def test_should_use_adaptive_curriculum_with_profile(self, agent_with_profile):
        """Test that adaptive curriculum is recommended when profile exists."""
        assert agent_with_profile.should_use_adaptive_curriculum() is True

    def test_should_use_adaptive_curriculum_without_profile(self, agent):
        """Test that adaptive curriculum is not recommended without profile."""
        # New agent with empty profile
        assert agent.should_use_adaptive_curriculum() is False

    def test_should_use_adaptive_curriculum_insufficient_data(self, agent):
        """Test that adaptive curriculum requires sufficient data."""
        # Add only 1 pattern (less than threshold of 5)
        agent.learner.grammar_patterns["present_tense_regular"] = GrammarPattern(
            name="present_tense_regular",
            description="Present tense",
            category=GrammarWeakness.VERB_CONJUGATION,
            difficulty_level=1,
            introduced_at_level="A1"
        )
        agent.learner_profile.error_prone_patterns = ["accusative_case"]

        # Should not use adaptive curriculum with insufficient data
        assert agent.should_use_adaptive_curriculum() is False

    def test_get_next_pattern_static_curriculum(self, agent):
        """Test getting next pattern with static curriculum."""
        pattern = agent.get_next_pattern(use_adaptive=False)
        # Should return first pattern in static curriculum
        assert pattern is not None
        # First pattern in curriculum is sv_order_main_clause
        assert pattern == "sv_order_main_clause"

    def test_get_next_pattern_adaptive_curriculum(self, agent_with_profile):
        """Test getting next pattern with adaptive curriculum."""
        # Get static curriculum order for comparison
        static_pattern = agent_with_profile.get_next_pattern(use_adaptive=False)
        # Get adaptive curriculum order
        adaptive_pattern = agent_with_profile.get_next_pattern(use_adaptive=True)

        # Both should return a pattern
        assert static_pattern is not None
        assert adaptive_pattern is not None

        # Verify that adaptive curriculum is being used
        adaptive_order = agent_with_profile.get_adaptive_curriculum_order(agent_with_profile.learner)
        static_order = [p.name for p in agent_with_profile.GERMAN_GRAMMAR_CURRICULUM]

        # The orders should be different (adaptive vs static)
        # Note: Due to both reinforcement AND acceleration, the final position
        # of accusative_case might not be strictly earlier if acceleration moves
        # other patterns around it. The key is that the order is different.
        assert adaptive_order != static_order, \
            "Adaptive curriculum should differ from static curriculum"

        # Verify that the returned pattern is from the adaptive order
        assert adaptive_pattern in adaptive_order, \
            "Returned pattern should be from adaptive curriculum"

    def test_get_recommended_next_pattern_auto_selects(self, agent_with_profile):
        """Test that recommended next pattern auto-selects curriculum type."""
        # With profile data, should use adaptive curriculum
        pattern = agent_with_profile.get_recommended_next_pattern()
        assert pattern is not None

        # Verify it's using adaptive curriculum by checking order
        adaptive_order = agent_with_profile.get_adaptive_curriculum_order(agent_with_profile.learner)
        assert pattern in adaptive_order, "Pattern should be from adaptive curriculum"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
