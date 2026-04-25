#!/usr/bin/env python
"""
Test script for Phase 2 implementation of GrammarCurriculumAgent.

This script tests:
1. Teaching effectiveness tracking
2. Pattern usage checking in current turn
3. Learning style detection (throttled)
4. Learner profile updates from teaching results
5. Pending teaching action tracking across turns
6. Strategy statistics tracking
"""

import sys
import os

# Add parent directory to path to access src
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(parent_dir, 'src'))

from agents.grammar_curriculum import GrammarCurriculumAgent
from agents.base import AgentConfig
from models.learner import Learner, ConfidenceLevel
from models.grammar_teaching import StrategyStats, LearnerGrammarProfile
from models.grammar import GrammarPattern, GrammarWeakness


def test_effectiveness_tracking_basic():
    """Test basic teaching effectiveness tracking."""
    print("Testing basic effectiveness tracking...")

    # Create a test learner with some grammar patterns
    learner = Learner(
        learner_id="test_learner",
        target_language="german",
        confidence=ConfidenceLevel.MODERATE,
        current_cefr_level="A1"
    )

    # Add a grammar pattern
    learner.grammar_patterns["accusative_case"] = GrammarPattern(
        name="accusative_case",
        description="Accusative case for direct objects",
        category=GrammarWeakness.CASE,
        difficulty_level=2,
        introduced_at_level="A1"
    )

    # Create agent
    config = AgentConfig(
        name="test_grammar_agent",
        description="Test grammar curriculum agent"
    )
    agent = GrammarCurriculumAgent(config, learner, llm_client=None)

    # Simulate teaching action from previous turn
    agent._pending_teaching_action = {
        "pattern": "accusative_case",
        "teaching_approach": "explicit_explanation"
    }

    # Create current turn context with no errors (success)
    teaching_action = {
        "pattern": "accusative_case",
        "teaching_approach": "explicit_explanation",
        "action": "review_pattern"
    }

    result = {
        "action": "review_pattern",
        "executed": True
    }

    current_errors = []  # No errors = success

    context = agent._build_teaching_context({
        "errors": [],
        "learner_input": "Ich sehe einen Hund",
        "topic": "general",
        "flow_score": 0.7,
        "turn_number": 10
    })

    # Track effectiveness
    agent._track_teaching_effectiveness(
        teaching_action=teaching_action,
        result=result,
        current_turn_errors=current_errors,
        context=context
    )

    # Check that strategy was tracked
    assert "explicit_explanation" in agent.teaching_strategy_tracker, \
        "Strategy not tracked"

    stats = agent.teaching_strategy_tracker["explicit_explanation"]
    assert stats.attempts == 1, f"Expected 1 attempt, got {stats.attempts}"
    assert stats.successful_corrections == 1, \
        f"Expected 1 successful correction, got {stats.successful_corrections}"
    assert stats.success_rate == 1.0, f"Expected 100% success rate, got {stats.success_rate}"

    print("✓ Basic effectiveness tracking test passed")
    return agent


def test_effectiveness_tracking_with_errors():
    """Test effectiveness tracking when learner makes errors."""
    print("Testing effectiveness tracking with errors...")

    # Create learner
    learner = Learner(
        learner_id="test_learner",
        target_language="german",
        confidence=ConfidenceLevel.MODERATE,
        current_cefr_level="A1"
    )

    # Add a grammar pattern
    learner.grammar_patterns["accusative_case"] = GrammarPattern(
        name="accusative_case",
        description="Accusative case for direct objects",
        category=GrammarWeakness.CASE,
        difficulty_level=2,
        introduced_at_level="A1"
    )

    # Create agent
    config = AgentConfig(
        name="test_grammar_agent",
        description="Test grammar curriculum agent"
    )
    agent = GrammarCurriculumAgent(config, learner, llm_client=None)

    # Simulate teaching action from previous turn
    agent._pending_teaching_action = {
        "pattern": "accusative_case",
        "teaching_approach": "explicit_explanation"
    }

    # Create current turn context with errors (failure)
    teaching_action = {
        "pattern": "accusative_case",
        "teaching_approach": "explicit_explanation",
        "action": "review_pattern"
    }

    result = {
        "action": "review_pattern",
        "executed": True
    }

    # Add errors in the same category (case)
    current_errors = [
        {
            "type": "grammar",
            "pattern": "accusative_case",
            "category": "case",  # This matches the pattern's category
            "severity": "moderate"
        }
    ]

    context = agent._build_teaching_context({
        "errors": current_errors,
        "learner_input": "Ich sehe ein Hund",  # Wrong article
        "topic": "general",
        "flow_score": 0.7,
        "turn_number": 10
    })

    # Track effectiveness
    agent._track_teaching_effectiveness(
        teaching_action=teaching_action,
        result=result,
        current_turn_errors=current_errors,
        context=context
    )

    # Check that strategy was tracked with failure
    assert "explicit_explanation" in agent.teaching_strategy_tracker, \
        "Strategy not tracked"

    stats = agent.teaching_strategy_tracker["explicit_explanation"]
    assert stats.attempts == 1, f"Expected 1 attempt, got {stats.attempts}"
    assert stats.successful_corrections == 0, \
        f"Expected 0 successful corrections, got {stats.successful_corrections}"
    assert stats.success_rate == 0.0, f"Expected 0% success rate, got {stats.success_rate}"

    print("✓ Effectiveness tracking with errors test passed")
    return agent


def test_pattern_category_lookup():
    """Test _get_pattern_category() method."""
    print("Testing pattern category lookup...")

    learner = Learner(
        learner_id="test_learner",
        target_language="german",
        confidence=ConfidenceLevel.MODERATE
    )

    config = AgentConfig(name="test", description="test")
    agent = GrammarCurriculumAgent(config, learner, llm_client=None)

    # Test known pattern
    category = agent._get_pattern_category("accusative_case")
    assert category == "case", f"Expected 'case', got '{category}'"

    # Test unknown pattern
    category = agent._get_pattern_category("unknown_pattern")
    assert category == "general", f"Expected 'general' for unknown pattern, got '{category}'"

    print("✓ Pattern category lookup test passed")


def test_pending_action_tracking():
    """Test that pending teaching actions are tracked correctly."""
    print("Testing pending action tracking...")

    learner = Learner(
        learner_id="test_learner",
        target_language="german",
        confidence=ConfidenceLevel.MODERATE
    )

    config = AgentConfig(name="test", description="test")
    agent = GrammarCurriculumAgent(config, learner, llm_client=None)

    # Initially no pending action
    assert agent._pending_teaching_action is None, "Should start with no pending action"

    # After a teaching action, should store pending action
    teaching_action = {
        "pattern": "accusative_case",
        "teaching_approach": "explicit_explanation",
        "action": "introduce_pattern"
    }

    result = {
        "action": "introduce_pattern",
        "executed": True
    }

    context = agent._build_teaching_context({
        "errors": [],
        "learner_input": "test",
        "topic": "general",
        "flow_score": 0.7,
        "turn_number": 10
    })

    agent._track_teaching_effectiveness(
        teaching_action=teaching_action,
        result=result,
        current_turn_errors=[],
        context=context
    )

    # Should have pending action now
    assert agent._pending_teaching_action is not None, "Should have pending action after teaching"
    assert agent._pending_teaching_action["pattern"] == "accusative_case", \
        "Pending action pattern incorrect"

    # After a "wait" action, pending action should be cleared
    teaching_action_wait = {
        "pattern": None,
        "teaching_approach": "none",
        "action": "wait"
    }

    result_wait = {
        "action": "wait",
        "executed": True
    }

    agent._track_teaching_effectiveness(
        teaching_action=teaching_action_wait,
        result=result_wait,
        current_turn_errors=[],
        context=context
    )

    # Should have no pending action now
    assert agent._pending_teaching_action is None, "Pending action should be cleared after wait"

    print("✓ Pending action tracking test passed")


def test_learner_profile_updates():
    """Test that learner profile is updated from teaching results."""
    print("Testing learner profile updates...")

    learner = Learner(
        learner_id="test_learner",
        target_language="german",
        confidence=ConfidenceLevel.MODERATE
    )

    config = AgentConfig(name="test", description="test")
    agent = GrammarCurriculumAgent(config, learner, llm_client=None)

    # Simulate successful teaching
    agent.learner_profile.update_from_teaching_result(
        pattern="accusative_case",
        strategy="explicit_explanation",
        success=True,
        pattern_mastery_data={
            "attempts": 2,
            "mastery_score": 0.8
        }
    )

    # Check that effective method was added
    assert "explicit_explanation" in agent.learner_profile.effective_teaching_methods, \
        "Effective method not added"

    # Check that pattern was added to strengths (quick mastery)
    assert "accusative_case" in agent.learner_profile.strength_patterns, \
        "Pattern not added to strengths"

    # Simulate failed teaching
    agent.learner_profile.update_from_teaching_result(
        pattern="dative_case",
        strategy="pattern_highlighting",
        success=False,
        pattern_mastery_data=None
    )

    # Check that ineffective method was added (since we have comparison data)
    assert "pattern_highlighting" in agent.learner_profile.ineffective_teaching_methods, \
        "Ineffective method not added"

    # Check that pattern was added to error-prone
    assert "dative_case" in agent.learner_profile.error_prone_patterns, \
        "Pattern not added to error-prone"

    print("✓ Learner profile updates test passed")


def test_learning_style_detection_throttling():
    """Test that learning style detection is throttled correctly."""
    print("Testing learning style detection throttling...")

    learner = Learner(
        learner_id="test_learner",
        target_language="german",
        confidence=ConfidenceLevel.MODERATE
    )

    config = AgentConfig(name="test", description="test")
    agent = GrammarCurriculumAgent(config, learner, llm_client=None)

    # Check initial state
    assert agent._learning_style_detection_turns == 0, "Should start at 0 turns"
    assert agent._learning_style_detection_interval == 50, "Should have interval of 50"

    # Create context
    context = agent._build_teaching_context({
        "errors": [],
        "learner_input": "test",
        "topic": "general",
        "flow_score": 0.7,
        "turn_number": 1
    })

    # Call detection 49 times - should not trigger actual detection (no LLM client)
    for i in range(49):
        agent._detect_learning_style(context)

    # Counter should be at 49
    assert agent._learning_style_detection_turns == 49, \
        f"Expected 49 turns, got {agent._learning_style_detection_turns}"

    # Call one more time - should reset counter (even though LLM fails)
    agent._detect_learning_style(context)

    # Counter should be reset to 0
    assert agent._learning_style_detection_turns == 0, \
        f"Expected counter reset to 0, got {agent._learning_style_detection_turns}"

    print("✓ Learning style detection throttling test passed")


def test_persistence_with_phase2_data():
    """Test that Phase 2 data persists correctly."""
    print("Testing Phase 2 data persistence...")

    learner = Learner(
        learner_id="test_learner",
        target_language="german",
        confidence=ConfidenceLevel.MODERATE
    )

    config = AgentConfig(name="test", description="test")
    agent = GrammarCurriculumAgent(config, learner, llm_client=None)

    # Add some Phase 2 data
    agent.teaching_strategy_tracker["explicit_explanation"] = StrategyStats(
        strategy_name="explicit_explanation",
        attempts=10,
        successful_corrections=7,
        learner_engagement=0.8,
        avg_mastery_improvement=0.2
    )

    agent.learner_profile.learning_style = "analytical"
    agent.learner_profile.effective_teaching_methods.append("explicit_explanation")
    agent.learner_profile.strength_patterns.append("accusative_case")
    agent.learner_profile.error_prone_patterns.append("dative_case")

    agent._pending_teaching_action = {
        "pattern": "accusative_case",
        "teaching_approach": "explicit_explanation",
        "timestamp": "2024-01-01T00:00:00"
    }

    # Save state
    agent._save_teaching_state()

    # Check saved state
    assert agent.learner.grammar_teaching_state is not None, \
        "Teaching state should be saved to learner"

    state = agent.learner.grammar_teaching_state
    assert "strategy_tracker" in state, "Missing strategy_tracker"
    assert "learner_profile" in state, "Missing learner_profile"
    assert "pending_action" in state, "Missing pending_action"

    # Create new agent and load state
    new_agent = GrammarCurriculumAgent(config, learner, llm_client=None)
    new_agent._load_teaching_state()

    # Check loaded state
    assert "explicit_explanation" in new_agent.teaching_strategy_tracker, \
        "Strategy tracker not loaded"

    loaded_stats = new_agent.teaching_strategy_tracker["explicit_explanation"]
    assert loaded_stats.attempts == 10, "Attempts not loaded correctly"
    assert loaded_stats.successful_corrections == 7, "Successful corrections not loaded"

    assert new_agent.learner_profile.learning_style == "analytical", \
        "Learning style not loaded"

    assert "explicit_explanation" in new_agent.learner_profile.effective_teaching_methods, \
        "Effective methods not loaded"

    assert "accusative_case" in new_agent.learner_profile.strength_patterns, \
        "Strength patterns not loaded"

    assert "dative_case" in new_agent.learner_profile.error_prone_patterns, \
        "Error-prone patterns not loaded"

    assert new_agent._pending_teaching_action is not None, \
        "Pending action not loaded"

    print("✓ Phase 2 data persistence test passed")


def test_full_process_loop_with_learning():
    """Test the full process() loop with learning enabled."""
    print("Testing full process() loop with Phase 2 learning...")

    learner = Learner(
        learner_id="test_learner",
        target_language="german",
        confidence=ConfidenceLevel.MODERATE,
        current_cefr_level="A1"
    )

    # Add a grammar pattern
    learner.grammar_patterns["accusative_case"] = GrammarPattern(
        name="accusative_case",
        description="Accusative case for direct objects",
        category=GrammarWeakness.CASE,
        difficulty_level=2,
        introduced_at_level="A1"
    )

    config = AgentConfig(name="test", description="test")
    agent = GrammarCurriculumAgent(config, learner, llm_client=None)

    # Set pending action from previous turn
    agent._pending_teaching_action = {
        "pattern": "accusative_case",
        "teaching_approach": "explicit_explanation"
    }

    # Process a turn (this should trigger effectiveness tracking)
    input_data = {
        "errors": [],  # No errors this time
        "learner_input": "Ich sehe einen Hund",
        "topic": "general",
        "flow_score": 0.7,
        "turn_number": 10
    }

    result = agent.process(input_data)

    # Check result structure
    assert "action" in result, "Missing action in result"
    assert "patterns_updated" in result, "Missing patterns_updated"
    assert "reasoning" in result, "Missing reasoning"

    # Check that strategy was tracked
    assert "explicit_explanation" in agent.teaching_strategy_tracker, \
        "Strategy should be tracked after process()"

    stats = agent.teaching_strategy_tracker["explicit_explanation"]
    assert stats.attempts == 1, "Should have 1 attempt tracked"
    assert stats.successful_corrections == 1, "Should have 1 success (no errors)"

    print("✓ Full process() loop with learning test passed")


def main():
    """Run all Phase 2 tests."""
    print("=" * 60)
    print("Phase 2 Implementation Tests: Learning & Adaptation")
    print("=" * 60)
    print()

    try:
        # Test 1: Basic effectiveness tracking
        test_effectiveness_tracking_basic()
        print()

        # Test 2: Effectiveness tracking with errors
        test_effectiveness_tracking_with_errors()
        print()

        # Test 3: Pattern category lookup
        test_pattern_category_lookup()
        print()

        # Test 4: Pending action tracking
        test_pending_action_tracking()
        print()

        # Test 5: Learner profile updates
        test_learner_profile_updates()
        print()

        # Test 6: Learning style detection throttling
        test_learning_style_detection_throttling()
        print()

        # Test 7: Phase 2 data persistence
        test_persistence_with_phase2_data()
        print()

        # Test 8: Full process loop with learning
        test_full_process_loop_with_learning()
        print()

        print("=" * 60)
        print("✓ ALL PHASE 2 TESTS PASSED!")
        print("=" * 60)
        print()
        print("Phase 2 implementation is working correctly:")
        print("  ✓ Teaching effectiveness tracking")
        print("  ✓ Pattern usage checking")
        print("  ✓ Learning style detection (with throttling)")
        print("  ✓ Learner profile updates")
        print("  ✓ Pending action tracking across turns")
        print("  ✓ Strategy statistics tracking")
        print("  ✓ Full persistence of learning data")
        print()
        return 0

    except AssertionError as e:
        print(f"✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
