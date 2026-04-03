"""
Integration tests for the agentic orchestrator system.

These tests verify that the new ReAct-based orchestration works correctly.
"""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.conversation import ConversationAgent
from agents.base import AgentConfig
from models.learner import Learner, ConfidenceLevel
from llm.client import LLMClient


def test_orchestrator_agent_creation():
    """Test that the agentic ConversationAgent can be created with all specialists."""
    # Create a mock LLM client
    mock_llm = Mock(spec=LLMClient)
    mock_llm.analyze_learner_input = Mock(return_value={
        "errors": [],
        "vocabulary_used": [],
        "intended_meaning": "Hello",
        "naturalness": "natural",
        "confidence_level": "high"
    })

    # Create a learner
    learner = Learner(
        learner_id="test_learner",
        native_language="english",
        target_language="german",
        current_cefr_level="A1",
        confidence=ConfidenceLevel.MODERATE
    )

    # Create agent config
    config = AgentConfig(
        name="conversation_orchestrator",
        description="Agentic conversation orchestrator",
        target_language="german"
    )

    # Create the agent
    agent = ConversationAgent(
        config=config,
        learner=learner,
        llm_client=mock_llm
    )

    # Verify specialists are available
    assert agent.grammar_curriculum_agent is not None
    assert agent.pronunciation_teaching_agent is not None

    print("✓ Agent creation test passed")


def test_orchestrator_has_react_loop():
    """Test that the agent has the ReAct loop methods."""
    mock_llm = Mock(spec=LLMClient)
    mock_llm.analyze_learner_input = Mock(return_value={
        "errors": [],
        "vocabulary_used": [],
        "intended_meaning": "Hello",
        "naturalness": "natural",
        "confidence_level": "high"
    })

    learner = Learner(
        learner_id="test_learner",
        native_language="english",
        target_language="german",
        current_cefr_level="A1",
        confidence=ConfidenceLevel.MODERATE
    )

    config = AgentConfig(
        name="conversation_orchestrator",
        description="Agentic conversation orchestrator",
        target_language="german"
    )

    agent = ConversationAgent(
        config=config,
        learner=learner,
        llm_client=mock_llm
    )

    # Check that the new helper methods exist
    assert hasattr(agent, '_get_learner_state_summary')
    assert hasattr(agent, '_call_specialist')
    assert hasattr(agent, '_synthesize_response')
    assert hasattr(agent, '_update_learner_from_specialists')
    assert hasattr(agent, 'orchestration_history')

    print("✓ ReAct loop methods test passed")


def test_orchestration_uses_llm_reasoning():
    """Test that orchestration calls generate_orchestration_plan."""
    mock_llm = Mock(spec=LLMClient)

    # Mock the analyze_learner_input call
    mock_llm.analyze_learner_input = Mock(return_value={
        "errors": [
            {
                "type": "grammar",
                "severity": "moderate",
                "description": "Wrong word order",
                "correction": "Ich spiele Fußball",
                "pattern": "sv_order_main_clause"
            }
        ],
        "vocabulary_used": [{"word": "spielen", "translation": "to play", "part_of_speech": "verb"}],
        "intended_meaning": "I play football",
        "naturalness": "natural",
        "confidence_level": "medium"
    })

    # Mock the orchestration plan call
    mock_llm.generate_orchestration_plan = Mock(return_value={
        "thoughts": "Learner made a word order error. Should track it and continue.",
        "actions": [
            {"specialist": "grammar_curriculum", "purpose": "track_error", "priority": 1}
        ],
        "teaching_strategy": "gentle_correction",
        "confidence": 0.9,
        "response_guidance": "Correct the error gently and continue"
    })

    # Mock the response generation
    mock_llm.generate_teaching_response = Mock(return_value="Gut! Fast richtig. Wir sagen 'Ich spiele Fußball.'")

    learner = Learner(
        learner_id="test_learner",
        native_language="english",
        target_language="german",
        current_cefr_level="A1",
        confidence=ConfidenceLevel.MODERATE
    )

    config = AgentConfig(
        name="conversation_orchestrator",
        description="Agentic conversation orchestrator",
        target_language="german"
    )

    agent = ConversationAgent(
        config=config,
        learner=learner,
        llm_client=mock_llm
    )

    # Process a learner input
    result = agent.process({
        "learner_input": "Ich Fußball spielen",
        "conversation_context": {"topic": "hobbies"}
    })

    # Verify the orchestration was called
    mock_llm.generate_orchestration_plan.assert_called_once()

    # Verify result structure
    assert "response" in result
    assert "orchestration" in result
    assert "specialist_results" in result
    assert result["orchestration"]["teaching_strategy"] == "gentle_correction"

    print("✓ Orchestration LLM reasoning test passed")


if __name__ == "__main__":
    print("Running agentic orchestrator integration tests...\n")
    test_orchestrator_agent_creation()
    test_orchestrator_has_react_loop()
    test_orchestration_uses_llm_reasoning()
    print("\n✅ All integration tests passed!")
