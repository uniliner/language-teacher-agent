"""
Test the retry logic for orchestration.

This demonstrates how the system handles invalid JSON from the LLM.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import os

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Set a dummy API key so LLMClient can be instantiated
os.environ["ANTHROPIC_API_KEY"] = "dummy-key-for-testing"

from llm.client import LLMClient


def test_retry_logic_with_invalid_json():
    """Test that the system retries when LLM returns invalid JSON."""

    print("\n=== Testing Retry Logic ===\n")

    # Create a real LLM client instance
    client = LLMClient(api_key="dummy-key-for-testing")

    # Simulate LLM returning invalid JSON first, then valid JSON
    call_count = [0]

    def mock_create(*args, **kwargs):
        call_count[0] += 1

        if call_count[0] == 1:
            # First call: Invalid JSON (missing closing brace)
            print(f"[Test] Call {call_count[0]}: Returning INVALID JSON")
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text='{"thoughts": "Learner needs help", "actions": [], "teaching_strategy": "gentle_correction"')]
            return mock_response
        else:
            # Second call: Valid JSON
            print(f"[Test] Call {call_count[0]}: Returning VALID JSON")
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text='''{"thoughts": "Learner made a grammar error. Should track it gently.", "actions": [{"specialist": "grammar_curriculum", "purpose": "track_error", "priority": 1}], "teaching_strategy": "gentle_correction", "confidence": 0.9, "response_guidance": "Correct error gently and continue"}''')]
            return mock_response

    # Patch the client's messages.create method
    with patch.object(client.client.messages, 'create', side_effect=mock_create):
        # Test the orchestration with retry logic
        result = client.generate_orchestration_plan(
            learner_input="Ich habe ein Hund",
            detected_errors=[{
                "type": "grammar",
                "severity": "moderate",
                "description": "Wrong article",
                "correction": "einen Hund"
            }],
            learner_state={
                "confidence": "MODERATE",
                "cefr_level": "A1",
                "total_turns": 5,
                "vocabulary_size": 20
            },
            conversation_context={
                "topic": "pets",
                "turn_number": 3,
                "flow_score": 0.7
            }
        )

        print(f"\n[Test] Final result after {call_count[0]} attempts:")
        print(f"  - Thoughts: {result['thoughts']}")
        print(f"  - Strategy: {result['teaching_strategy']}")
        print(f"  - Actions: {len(result['actions'])} specialist(s)")
        print(f"  - Fallback used: {result.get('fallback_used', False)}")

        # Verify that retry happened
        assert call_count[0] == 2, f"Expected 2 calls, got {call_count[0]}"
        assert result["teaching_strategy"] == "gentle_correction"
        assert len(result["actions"]) == 1
        assert result["actions"][0]["specialist"] == "grammar_curriculum"
        assert not result.get("fallback_used", False), "Should not use fallback after successful retry"

        print("\n✅ Retry logic test passed!")


def test_fallback_after_all_retries_exhausted():
    """Test that fallback is used after all retry attempts fail."""

    print("\n=== Testing Fallback After Retries Exhausted ===\n")

    # Create a real LLM client instance
    client = LLMClient(api_key="dummy-key-for-testing")

    call_count = [0]

    def mock_create_always_fail(*args, **kwargs):
        call_count[0] += 1
        print(f"[Test] Call {call_count[0]}: Returning INVALID JSON (will always fail)")

        # Always return invalid JSON
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='This is not JSON at all! Just some random text that cannot be parsed.')]
        return mock_response

    # Patch the client's messages.create method
    with patch.object(client.client.messages, 'create', side_effect=mock_create_always_fail):
        # Test the orchestration with retry logic
        result = client.generate_orchestration_plan(
            learner_input="Ich habe ein Hund",
            detected_errors=[{
                "type": "grammar",
                "severity": "moderate",
                "description": "Wrong article",
                "correction": "einen Hund"
            }],
            learner_state={
                "confidence": "MODERATE",
                "cefr_level": "A1",
                "total_turns": 5,
                "vocabulary_size": 20
            },
            conversation_context={
                "topic": "pets",
                "turn_number": 3,
                "flow_score": 0.7
            }
        )

        print(f"\n[Test] Final result after {call_count[0]} attempts:")
        print(f"  - Thoughts: {result['thoughts'][:80]}...")
        print(f"  - Strategy: {result['teaching_strategy']}")
        print(f"  - Fallback used: {result.get('fallback_used', False)}")
        print(f"  - Fallback reason: {result.get('fallback_reason', 'N/A')}")

        # Verify that all retries were exhausted and fallback was used
        assert call_count[0] == 3, f"Expected 3 retry attempts, got {call_count[0]}"
        assert result.get("fallback_used", True), "Should use fallback after all retries fail"
        assert result["teaching_strategy"] == "gentle_correction"
        assert len(result["actions"]) == 1
        assert result["actions"][0]["specialist"] == "grammar_curriculum"

        print("\n✅ Fallback after retries exhausted test passed!")


if __name__ == "__main__":
    print("Running retry logic tests...\n")
    test_retry_logic_with_invalid_json()
    test_fallback_after_all_retries_exhausted()
    print("\n" + "="*50)
    print("✅ All retry logic tests passed!")
    print("="*50)
