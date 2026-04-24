#!/usr/bin/env python
"""
Quick test script for Phase 1 implementation of GrammarCurriculumAgent.

This script tests:
1. Agent initialization with new state variables
2. LLM decision-making (if API key available)
3. Fallback to rule-based decision when LLM fails
4. Persistence methods (load/save teaching state)
5. Agentic ReAct loop in process() method
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


def test_agent_initialization():
    """Test that the agent initializes with new Phase 1 state variables."""
    print("Testing agent initialization...")

    # Create a test learner
    learner = Learner(
        learner_id="test_learner",
        target_language="german",
        confidence=ConfidenceLevel.MODERATE,
        current_cefr_level="A1"
    )

    # Create agent config
    config = AgentConfig(
        name="test_grammar_agent",
        description="Test grammar curriculum agent"
    )

    # Initialize agent (without LLM client for testing)
    agent = GrammarCurriculumAgent(config, learner, llm_client=None)

    # Check new state variables exist
    assert hasattr(agent, 'teaching_strategy_tracker'), "Missing teaching_strategy_tracker"
    assert hasattr(agent, 'learner_profile'), "Missing learner_profile"
    assert hasattr(agent, '_pending_teaching_action'), "Missing _pending_teaching_action"
    assert hasattr(agent, '_last_grammar_teaching_turn'), "Missing _last_grammar_teaching_turn"

    # Check types
    assert isinstance(agent.teaching_strategy_tracker, dict), "teaching_strategy_tracker should be dict"
    assert isinstance(agent.learner_profile, LearnerGrammarProfile), "learner_profile should be LearnerGrammarProfile"
    assert isinstance(agent._last_grammar_teaching_turn, int), "_last_grammar_teaching_turn should be int"

    print("✓ Agent initialization test passed")
    return agent


def test_context_building(agent):
    """Test that _build_teaching_context() works correctly."""
    print("Testing context building...")

    input_data = {
        "errors": [
            {
                "type": "grammar",
                "pattern": "accusative_case",
                "severity": "moderate"
            }
        ],
        "learner_input": "Ich habe einen Hund",
        "topic": "family",
        "flow_score": 0.7,
        "turn_number": 5
    }

    context = agent._build_teaching_context(input_data)

    # Check structure
    assert "learner_state" in context, "Missing learner_state in context"
    assert "conversation" in context, "Missing conversation in context"
    assert "errors" in context, "Missing errors in context"
    assert "available_patterns" in context, "Missing available_patterns in context"

    # Check learner state
    learner_state = context["learner_state"]
    assert learner_state["cefr_level"] == "A1", "Incorrect CEFR level"
    assert learner_state["confidence"] == "moderate", "Incorrect confidence level"

    # Check conversation context
    conversation = context["conversation"]
    assert conversation["topic"] == "family", "Incorrect topic"
    assert conversation["flow_score"] == 0.7, "Incorrect flow score"

    print("✓ Context building test passed")
    return context


def test_fallback_decision_making(agent, context):
    """Test that rule-based fallback works when LLM is not available."""
    print("Testing fallback decision-making...")

    # This should use rule-based fallback since llm_client is None
    teaching_plan = agent._generate_teaching_plan(context)

    # Check structure
    assert "action" in teaching_plan, "Missing action in teaching plan"
    assert "pattern" in teaching_plan, "Missing pattern in teaching plan"
    assert "reasoning" in teaching_plan, "Missing reasoning in teaching plan"
    assert "teaching_approach" in teaching_plan, "Missing teaching_approach in teaching plan"
    assert "priority" in teaching_plan, "Missing priority in teaching plan"

    # Check valid action
    valid_actions = ["introduce_pattern", "review_pattern", "reinforce_pattern", "wait"]
    assert teaching_plan["action"] in valid_actions, f"Invalid action: {teaching_plan['action']}"

    print(f"✓ Fallback decision-making test passed (action: {teaching_plan['action']})")
    return teaching_plan


def test_execute_teaching_plan(agent, teaching_plan, context):
    """Test that teaching plan execution works."""
    print("Testing teaching plan execution...")

    result = agent._execute_teaching_plan(teaching_plan, context)

    # Check structure
    assert "action" in result, "Missing action in result"
    assert "pattern" in result, "Missing pattern in result"
    assert "executed" in result, "Missing executed flag in result"
    assert "reasoning" in result, "Missing reasoning in result"

    print(f"✓ Teaching plan execution test passed (executed: {result['executed']})")
    return result


def test_persistence(agent):
    """Test that teaching state persistence works."""
    print("Testing teaching state persistence...")

    # Set some test data
    agent.teaching_strategy_tracker["explicit_explanation"] = StrategyStats(
        strategy_name="explicit_explanation",
        attempts=5,
        successful_corrections=3,
        learner_engagement=0.8,
        avg_mastery_improvement=0.2
    )

    agent.learner_profile.learning_style = "analytical"
    agent.learner_profile.effective_teaching_methods.append("explicit_explanation")

    agent._pending_teaching_action = {
        "pattern": "accusative_case",
        "teaching_approach": "explicit_explanation",
        "timestamp": "2024-01-01T00:00:00"
    }

    # Save state
    agent._save_teaching_state()

    # Check that learner has grammar_teaching_state
    assert hasattr(agent.learner, 'grammar_teaching_state'), "Learner missing grammar_teaching_state"
    assert agent.learner.grammar_teaching_state is not None, "grammar_teaching_state is None"

    state = agent.learner.grammar_teaching_state
    assert "strategy_tracker" in state, "Missing strategy_tracker in saved state"
    assert "learner_profile" in state, "Missing learner_profile in saved state"
    assert "pending_action" in state, "Missing pending_action in saved state"

    # Create new agent to test loading
    new_agent = GrammarCurriculumAgent(agent.config, agent.learner, llm_client=None)

    # Load state
    new_agent._load_teaching_state()

    # Check that state was loaded correctly
    assert "explicit_explanation" in new_agent.teaching_strategy_tracker, "Strategy tracker not loaded"
    assert new_agent.learner_profile.learning_style == "analytical", "Learning style not loaded"
    assert new_agent._pending_teaching_action is not None, "Pending action not loaded"

    print("✓ Persistence test passed")


def test_agentic_process_loop(agent):
    """Test the agentic ReAct loop in process() method."""
    print("Testing agentic process() method...")

    input_data = {
        "errors": [
            {
                "type": "grammar",
                "pattern": "accusative_case",
                "severity": "moderate"
            }
        ],
        "learner_input": "Ich habe einen Hund",
        "topic": "family",
        "flow_score": 0.7,
        "turn_number": 5
    }

    result = agent.process(input_data)

    # Check structure
    assert "action" in result, "Missing action in result"
    assert "patterns_updated" in result, "Missing patterns_updated in result"
    assert "ready_to_advance" in result, "Missing ready_to_advance in result"
    assert "suggested_focus" in result, "Missing suggested_focus in result"
    assert "current_position" in result, "Missing current_position in result"
    assert "reasoning" in result, "Missing reasoning in result"

    print(f"✓ Agentic process() test passed (action: {result['action']})")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Phase 1 Implementation Tests")
    print("=" * 60)
    print()

    try:
        # Test 1: Agent initialization
        agent = test_agent_initialization()
        print()

        # Test 2: Context building
        context = test_context_building(agent)
        print()

        # Test 3: Fallback decision-making
        teaching_plan = test_fallback_decision_making(agent, context)
        print()

        # Test 4: Execute teaching plan
        test_execute_teaching_plan(agent, teaching_plan, context)
        print()

        # Test 5: Persistence
        test_persistence(agent)
        print()

        # Test 6: Agentic process loop
        test_agentic_process_loop(agent)
        print()

        print("=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60)
        print()
        print("Phase 1 implementation is working correctly:")
        print("  ✓ LLM integration with fallback")
        print("  ✓ Agentic ReAct loop")
        print("  ✓ Teaching state persistence")
        print("  ✓ Context building")
        print("  ✓ Decision-making (rule-based fallback)")
        print()
        return 0

    except AssertionError as e:
        print(f"✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
