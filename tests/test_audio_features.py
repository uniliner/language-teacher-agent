#!/usr/bin/env python3
"""
Test script for audio features.

This script tests the basic audio functionality:
1. Speech synthesis (TTS)
2. Speech recording
3. Pronunciation assessment
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from speech import AzureSpeechClient, SpeechConfig


def test_speech_synthesis(client: AzureSpeechClient):
    """Test text-to-speech synthesis."""
    print("\n" + "=" * 60)
    print("Test 1: Speech Synthesis (Text-to-Speech)")
    print("=" * 60)

    test_texts = [
        "Guten Tag",  # Good day
        "Ich spreche Deutsch",  # I speak German
        "Die Aussprache ist wichtig",  # Pronunciation is important
    ]

    for text in test_texts:
        print(f"\nSynthesizing: '{text}'")
        audio = client.synthesize_speech(text)

        if audio:
            print(f"  ✓ Synthesis successful (audio size: {len(audio)} bytes)")

            # Play the audio
            print(f"  🔊 Playing audio...")
            if client.play_audio(audio):
                print(f"  ✓ Playback successful")
            else:
                print(f"  ✗ Playback failed")
        else:
            print(f"  ✗ Synthesis failed")


def test_speech_config():
    """Test speech configuration loading."""
    print("\n" + "=" * 60)
    print("Test 0: Speech Configuration")
    print("=" * 60)

    config = SpeechConfig.from_env()

    if config:
        print(f"  ✓ Configuration loaded successfully")
        print(f"    Region: {config.speech_region}")
        print(f"    Voice: {config.voice_name}")
        print(f"    Cache: {config.enable_cache}")
        print(f"    Cache dir: {config.cache_dir}")
        return config
    else:
        print("  ✗ Could not load configuration from environment")
        print("    Please set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION")
        return None


def test_pronunciation_assessment(client: AzureSpeechClient):
    """Test pronunciation assessment."""
    print("\n" + "=" * 60)
    print("Test 2: Pronunciation Assessment")
    print("=" * 60)

    test_words = [
        "Ich",
        "Deutsch",
        "Sprechen",
    ]

    for word in test_words:
        print(f"\nWord: '{word}'")
        print("  Get ready to speak...")

        # Play the example first
        audio = client.synthesize_speech(word)
        if audio:
            print("  🔊 Playing example...")
            client.play_audio(audio)

        # Ask user to press Enter when ready
        input("  Press Enter when ready to speak...")

        # Record and assess
        print("  🔴 Recording...")
        assessment = client.assess_pronunciation(word)

        if assessment:
            print(f"  ✓ Assessment completed")
            print(f"    Accuracy: {assessment.accuracy_score:.2%}")
            print(f"    Fluency: {assessment.fluency_score:.2%}")
            print(f"    Completeness: {assessment.completeness_score:.2%}")
            print(f"    Prosody: {assessment.prosody_score:.2%}")
            print(f"    Overall: {assessment.overall_score:.2%}")
            print(f"    Grade: {assessment.get_feedback_grade()}")
            print(f"    Feedback: {assessment.get_feedback_message()}")
        else:
            print("  ✗ Assessment failed")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Audio Features Test Suite")
    print("=" * 60)

    # Test configuration
    config = test_speech_config()
    if not config:
        print("\n❌ Cannot proceed without valid configuration")
        sys.exit(1)

    # Initialize client
    print("\nInitializing Azure Speech client...")
    try:
        client = AzureSpeechClient(config)
        print("  ✓ Client initialized successfully")
    except Exception as e:
        print(f"  ✗ Failed to initialize client: {e}")
        sys.exit(1)

    # Run tests
    try:
        # Test 1: Speech synthesis
        test_speech_synthesis(client)

        # Test 2: Pronunciation assessment (requires user interaction)
        print("\n" + "=" * 60)
        choice = input(
            "Would you like to test pronunciation assessment? "
            "This requires speaking into your microphone. (y/n): "
        ).strip().lower()

        if choice == 'y':
            test_pronunciation_assessment(client)
        else:
            print("Skipping pronunciation assessment test.")

        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\n⚠ Tests interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
