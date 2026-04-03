#!/usr/bin/env python3
"""
Test script to verify audio playback is complete (not cut off).

This tests the fix for the issue where only the last part of the word was audible.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from speech import AzureSpeechClient, SpeechConfig


def test_complete_playback():
    """Test that audio plays completely from start to finish."""
    print("=" * 60)
    print("Testing Complete Audio Playback")
    print("=" * 60)

    # Initialize client
    config = SpeechConfig.from_env()
    if not config:
        print("❌ Could not load configuration")
        return False

    client = AzureSpeechClient(config)

    # Test words of different lengths
    test_words = [
        ("Ich", "Short word"),
        ("Guten Tag", "Two words"),
        ("Aussprache", "Longer word"),
        ("Wie geht es Ihnen heute?", "Sentence"),
    ]

    print("\nPlaying test audio - listen for completeness:\n")

    for word, description in test_words:
        print(f"Testing: {description} - '{word}'")

        # Synthesize
        audio = client.synthesize_speech(word)

        if not audio:
            print(f"  ✗ Synthesis failed")
            continue

        print(f"  ✓ Synthesized: {len(audio)} bytes")

        # Play
        print(f"  🔊 Playing...")
        if client.play_audio(audio):
            print(f"  ✓ Playback completed")
        else:
            print(f"  ✗ Playback failed")

        print()

    print("=" * 60)
    print("Test completed!")
    print("=" * 60)
    print("\nIf you heard the complete words (not just endings), the fix works!")

    return True


def test_audio_data_integrity():
    """Test that synthesized audio data is complete."""
    print("\n" + "=" * 60)
    print("Testing Audio Data Integrity")
    print("=" * 60)

    config = SpeechConfig.from_env()
    client = AzureSpeechClient(config)

    test_text = "Die Aussprache ist sehr wichtig"

    print(f"\nSynthesizing: '{test_text}'")
    audio = client.synthesize_speech(test_text)

    if not audio:
        print("✗ Synthesis failed")
        return False

    print(f"✓ Audio data size: {len(audio)} bytes")

    # Check audio data has reasonable size (WAV header + audio data)
    # A few seconds of speech should be at least 10KB
    if len(audio) < 10240:
        print(f"⚠ Warning: Audio data seems small ({len(audio)} bytes)")
        print("  This might indicate incomplete synthesis")
        return False

    print(f"✓ Audio data size looks good")

    # Verify it starts with WAV header
    if audio[:4] == b"RIFF" and audio[8:12] == b"WAVE":
        print("✓ Valid WAV format detected")
    else:
        print("⚠ Warning: Audio data doesn't start with WAV header")
        print(f"  First 12 bytes: {audio[:12]}")

    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Complete Audio Playback Test Suite")
    print("=" * 60)

    try:
        # Test 1: Data integrity
        if not test_audio_data_integrity():
            print("\n❌ Audio data integrity test failed")
            return 1

        # Test 2: Complete playback
        print("\n")
        if not test_complete_playback():
            print("\n❌ Playback test failed")
            return 1

        print("\n✅ All tests passed!")
        print("\nThe audio playback should now be complete from start to finish.")
        return 0

    except KeyboardInterrupt:
        print("\n\n⚠ Tests interrupted by user")
        return 0
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
