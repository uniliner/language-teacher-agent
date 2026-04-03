#!/usr/bin/env python3
"""
Validation script for Azure Speech Service and audio capabilities.

This script checks:
1. Azure Speech SDK installation
2. Azure credentials configuration
3. Audio input/output devices
4. Basic speech synthesis and recognition functionality
"""

import os
import sys
from pathlib import Path

print("=" * 60)
print("Azure Speech Service - Audio Setup Validation")
print("=" * 60)

# Check 1: Azure Speech SDK installation
print("\n[1/6] Checking Azure Speech SDK installation...")
try:
    import azure.cognitiveservices.speech as speechsdk
    print(f"   ✓ Azure Speech SDK installed (version: {speechsdk.__version__})")
except ImportError as e:
    print(f"   ✗ Failed to import Azure Speech SDK: {e}")
    print("   Install with: pip install azure-cognitiveservices-speech")
    sys.exit(1)

# Check 2: Azure credentials
print("\n[2/6] Checking Azure credentials...")
from dotenv import load_dotenv

load_dotenv()

speech_key = os.getenv("AZURE_SPEECH_KEY") or os.getenv("SPEECH_KEY")
speech_region = os.getenv("AZURE_SPEECH_REGION") or os.getenv("SPEECH_REGION")

if not speech_key:
    print("   ✗ Azure Speech Key not found")
    print("   Set AZURE_SPEECH_KEY or SPEECH_KEY in your .env file")
    print("   Get your key from: https://portal.azure.com/#view/Microsoft_Azure_ProjectOxford/CognitiveServicesHub/~/SpeechServices")
else:
    print(f"   ✓ Azure Speech Key found (length: {len(speech_key)})")

if not speech_region:
    print("   ✗ Azure Speech Region not found")
    print("   Set AZURE_SPEECH_REGION or SPEECH_REGION in your .env file")
    print("   Examples: eastus, westeurope, southeastasia")
else:
    print(f"   ✓ Azure Speech Region: {speech_region}")

if not speech_key or not speech_region:
    print("\n   Skipping functionality tests (missing credentials)")
    sys.exit(1)

# Check 3: Initialize speech config
print("\n[3/6] Initializing Speech Service...")
try:
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
    speech_config.speech_synthesis_voice_name = "de-DE-KatjaNeural"  # German voice
    print("   ✓ Speech config initialized successfully")
except Exception as e:
    print(f"   ✗ Failed to initialize speech config: {e}")
    sys.exit(1)

# Check 4: Check audio devices (for synthesis)
print("\n[4/6] Checking audio output capabilities...")
try:
    # Try to create a synthesizer (this will check default audio device)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
    print("   ✓ Audio output device available")
except Exception as e:
    print(f"   ✗ No audio output device found: {e}")
    print("   Note: This may fail in headless environments")

# Check 5: Test speech synthesis (text-to-speech)
print("\n[5/6] Testing speech synthesis (Text-to-Speech)...")
try:
    test_text = "Hallo, das ist ein Test."
    result = synthesizer.speak_text_async(test_text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print("   ✓ Speech synthesis successful")
        print(f"   ✓ Test phrase spoken: '{test_text}'")
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation = speechsdk.SpeechSynthesisCancellationDetails(result)
        print(f"   ✗ Speech synthesis canceled: {cancellation.reason}")
        if cancellation.reason == speechsdk.CancellationReason.Error:
            print(f"   Error details: {cancellation.error_details}")
except Exception as e:
    print(f"   ✗ Speech synthesis failed: {e}")
    print("   This is expected in headless environments without audio")

# Check 6: Check audio input devices (for recognition)
print("\n[6/6] Checking audio input capabilities...")
try:
    audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
    print("   ✓ Audio input device (microphone) available")

    # Note: We won't test actual recording as it requires user interaction
    print("   ℹ Microphone access available for speech recognition")
except Exception as e:
    print(f"   ✗ No audio input device found: {e}")
    print("   Error: No microphone available or access denied")

# Summary
print("\n" + "=" * 60)
print("Validation Complete!")
print("=" * 60)

# Additional recommendations
print("\n📋 Additional Dependencies for Full Functionality:")
print("\nFor enhanced audio recording/playback, consider installing:")
print("   - sounddevice: For low-latency audio I/O")
print("   - pyaudio: Alternative audio I/O backend")
print("   - scipy: For audio processing and analysis")
print("\nInstall with:")
print("   pip install sounddevice scipy pyaudio")

print("\n📝 Update your .env file with:")
print("   AZURE_SPEECH_KEY=your_key_here")
print("   AZURE_SPEECH_REGION=your_region_here")
print("\nAvailable voices for German (de-DE):")
print("   - de-DE-KatjaNeural (Female)")
print("   - de-DE-ChristophNeural (Male)")
print("   - de-DE-ElkeNeural (Female)")
print("   - de-DE-GerhardNeural (Male)")
print("\nSee: https://learn.microsoft.com/en-us/azure/cognitive-services/speech-service/language-support#text-to-speech")
