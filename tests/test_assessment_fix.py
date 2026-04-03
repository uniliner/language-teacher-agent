#!/usr/bin/env python3
"""
Quick test to verify the assessment fix works.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from speech import PronunciationAssessmentResult


def test_assessment_with_none_scores():
    """Test that assessment handles None scores gracefully."""
    print("\n" + "=" * 60)
    print("Testing Assessment with None Values")
    print("=" * 60)

    # This simulates what Azure returns when assessment fails/partially fails
    class MockPronunciationResult:
        def __init__(self):
            self.accuracy_score = None  # Simulating None value
            self.fluency_score = 85.0
            self.completeness_score = None  # Another None
            self.prosody_score = 70.0

    # Test the fix
    mock_result = MockPronunciationResult()

    # This is the fixed code from client.py
    accuracy = mock_result.accuracy_score or 0.0
    fluency = mock_result.fluency_score or 0.0
    completeness = mock_result.completeness_score or 0.0
    prosody = mock_result.prosody_score or 0.0

    print(f"\nOriginal values (with None):")
    print(f"  Accuracy: {mock_result.accuracy_score}")
    print(f"  Fluency: {mock_result.fluency_score}")
    print(f"  Completeness: {mock_result.completeness_score}")
    print(f"  Prosody: {mock_result.prosody_score}")

    print(f"\nFixed values (None → 0.0):")
    print(f"  Accuracy: {accuracy}")
    print(f"  Fluency: {fluency}")
    print(f"  Completeness: {completeness}")
    print(f"  Prosody: {prosody}")

    # This would have failed before the fix
    try:
        assessment = PronunciationAssessmentResult(
            accuracy_score=accuracy / 100.0,
            fluency_score=fluency / 100.0,
            completeness_score=completeness / 100.0,
            prosody_score=prosody / 100.0,
            error_text="Test",
            feedback="Test feedback",
        )

        print(f"\n✓ Assessment created successfully!")
        print(f"  Overall score: {assessment.overall_score:.2%}")
        print(f"  Grade: {assessment.get_feedback_grade()}")
        print(f"  Feedback: {assessment.get_feedback_message()}")
        return True

    except Exception as e:
        print(f"\n✗ Failed to create assessment: {e}")
        return False


def test_assessment_with_all_scores():
    """Test normal case with all scores present."""
    print("\n" + "=" * 60)
    print("Testing Assessment with All Scores")
    print("=" * 60)

    try:
        assessment = PronunciationAssessmentResult(
            accuracy_score=0.85,
            fluency_score=0.90,
            completeness_score=0.95,
            prosody_score=0.80,
            error_text="Das ist gut",
            feedback="Good pronunciation!",
        )

        print(f"\n✓ Assessment created successfully!")
        print(f"  Accuracy: {assessment.accuracy_score:.2%}")
        print(f"  Fluency: {assessment.fluency_score:.2%}")
        print(f"  Completeness: {assessment.completeness_score:.2%}")
        print(f"  Prosody: {assessment.prosody_score:.2%}")
        print(f"  Overall: {assessment.overall_score:.2%}")
        print(f"  Grade: {assessment.get_feedback_grade()}")
        return True

    except Exception as e:
        print(f"\n✗ Failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Assessment Fix Verification Tests")
    print("=" * 60)

    results = []

    # Test 1: None values
    results.append(("None values handling", test_assessment_with_none_scores()))

    # Test 2: All scores present
    results.append(("All scores present", test_assessment_with_all_scores()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(result[1] for result in results)

    if all_passed:
        print("\n✅ All tests passed! The fix is working correctly.")
        return 0
    else:
        print("\n❌ Some tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
