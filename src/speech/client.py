"""
Main Azure Speech Service client.

This module provides the primary interface for all Azure Speech Service operations
including text-to-speech, speech recognition, and pronunciation assessment.
"""

import hashlib
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import azure.cognitiveservices.speech as speechsdk

from .config import SpeechConfig
from .models import AudioRecording, PronunciationAssessmentResult

logger = logging.getLogger(__name__)


class AzureSpeechClient:
    """
    Main client for Azure Speech Service operations.

    This class provides a unified interface for:
    - Text-to-speech synthesis
    - Speech recording from microphone
    - Pronunciation assessment
    - Audio playback
    """

    def __init__(self, config: SpeechConfig):
        """
        Initialize the Azure Speech client.

        Args:
            config: Speech configuration with credentials and settings
        """
        if not config.is_configured:
            raise ValueError("Speech configuration is missing credentials")

        self.config = config
        self._init_azure_sdk()

        # Ensure cache directory exists
        if config.enable_cache:
            config.ensure_cache_dir()

    def _init_azure_sdk(self) -> None:
        """Initialize Azure Speech SDK configuration."""
        self.speech_config = speechsdk.SpeechConfig(
            subscription=self.config.speech_key, region=self.config.speech_region
        )

        # Set the voice for German TTS
        self.speech_config.speech_synthesis_voice_name = self.config.voice_name

        logger.debug(f"Azure Speech SDK initialized with voice: {self.config.voice_name}")

    def synthesize_speech(self, text: str, language: str = "de-DE") -> Optional[bytes]:
        """
        Synthesize speech from text.

        Args:
            text: Text to synthesize
            language: Language code (default: de-DE for German)

        Returns:
            Audio bytes in WAV format, or None if synthesis fails
        """
        # Check cache first
        if self.config.enable_cache:
            cached_audio = self._get_cached_audio(text)
            if cached_audio:
                logger.debug(f"Using cached audio for: {text[:50]}...")
                return cached_audio

        try:
            # Create synthesizer
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=self.speech_config, audio_config=None
            )

            # Synthesize
            logger.debug(f"Starting synthesis for: {text[:50]}...")
            result = synthesizer.speak_text_async(text).get()

            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                audio_data = result.audio_data

                if not audio_data or len(audio_data) == 0:
                    logger.error("Synthesis completed but returned empty audio data")
                    return None

                logger.info(f"Synthesis completed: {len(audio_data)} bytes for '{text[:50]}...'")

                # Cache the result
                if self.config.enable_cache:
                    self._cache_audio(text, audio_data)

                return audio_data

            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation = speechsdk.SpeechSynthesisCancellationDetails(result)
                logger.error(f"Speech synthesis canceled: {cancellation.reason}")
                if cancellation.reason == speechsdk.CancellationReason.Error:
                    logger.error(f"Error details: {cancellation.error_details}")
                return None

        except Exception as e:
            logger.error(f"Speech synthesis failed: {e}")
            return None

        return None

    def record_speech(self, timeout_seconds: int = 5) -> Optional[AudioRecording]:
        """
        Record speech from microphone.

        Args:
            timeout_seconds: Maximum recording duration

        Returns:
            AudioRecording object, or None if recording fails
        """
        try:
            # Configure audio input from default microphone
            audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)

            # Create recognizer
            recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config, audio_config=audio_config
            )

            logger.info(f"Starting recording (timeout: {timeout_seconds}s)...")

            # Record with timeout
            result = recognizer.recognize_once_async().get()

            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                # Note: Azure Speech SDK doesn't directly provide audio data
                # for recognition. We get the text result.
                # For full audio recording, we'd need to use PullAudioOutputStream
                # which is more complex. For now, we'll store metadata.

                duration_ms = result.duration  # Duration in 100-nanosecond units
                duration_ms = duration_ms // 10000  # Convert to milliseconds

                recording = AudioRecording(
                    audio_data=b"",  # Empty for now - would need PullAudioOutputStream
                    duration_ms=duration_ms,
                    timestamp=datetime.now(),
                )

                logger.info(f"Recording completed: {result.text}")
                return recording

            elif result.reason == speechsdk.ResultReason.NoMatch:
                logger.warning("No speech detected in recording")
                return None

            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation = speechsdk.SpeechRecognitionCancellationDetails(result)
                logger.error(f"Recording canceled: {cancellation.reason}")
                if cancellation.reason == speechsdk.CancellationReason.Error:
                    logger.error(f"Error details: {cancellation.error_details}")
                return None

        except Exception as e:
            logger.error(f"Recording failed: {e}")
            return None

        return None

    def assess_pronunciation(
        self, reference_text: str, timeout_seconds: int = 5
    ) -> Optional[PronunciationAssessmentResult]:
        """
        Assess pronunciation against reference text.

        Uses Azure Speech Service's pronunciation assessment feature
        to score accuracy, fluency, and completeness.

        Args:
            reference_text: The target text to compare against
            timeout_seconds: Maximum recording duration

        Returns:
            PronunciationAssessmentResult with scores and feedback
        """
        try:
            # Create pronunciation assessment config
            pronunciation_assessment_config = speechsdk.PronunciationAssessmentConfig(
                reference_text=reference_text,
                grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
                granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
                enable_miscue=True,
            )

            # Configure audio input
            audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)

            # Create recognizer with assessment config
            recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config, audio_config=audio_config
            )

            pronunciation_assessment_config.apply_to(recognizer)

            logger.info(f"Starting pronunciation assessment for: {reference_text}")

            # Recognize with assessment
            result = recognizer.recognize_once_async().get()

            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                # Extract pronunciation assessment results
                pronunciation_result = speechsdk.PronunciationAssessmentResult(result)

                # Handle None values safely
                accuracy = pronunciation_result.accuracy_score or 0.0
                fluency = pronunciation_result.fluency_score or 0.0
                completeness = pronunciation_result.completeness_score or 0.0
                prosody = pronunciation_result.prosody_score or 0.0

                assessment = PronunciationAssessmentResult(
                    accuracy_score=accuracy / 100.0,
                    fluency_score=fluency / 100.0,
                    completeness_score=completeness / 100.0,
                    prosody_score=prosody / 100.0,
                    error_text=result.text,
                    feedback=self._generate_assessment_feedback(pronunciation_result),
                )

                logger.info(
                    f"Pronunciation assessment completed: {assessment.overall_score:.2%}"
                )
                return assessment

            elif result.reason == speechsdk.ResultReason.NoMatch:
                logger.warning("No speech detected for assessment")
                return None

            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation = speechsdk.SpeechRecognitionCancellationDetails(result)
                logger.error(f"Assessment canceled: {cancellation.reason}")
                return None

        except Exception as e:
            logger.error(f"Pronunciation assessment failed: {e}")
            return None

        return None

    def play_audio(self, audio_data: bytes) -> bool:
        """
        Play audio through default output device.

        Args:
            audio_data: Audio bytes in WAV format

        Returns:
            True if playback succeeded, False otherwise
        """
        import tempfile
        import platform
        import time

        try:
            # Validate audio data
            if not audio_data or len(audio_data) < 100:
                logger.warning(f"Audio data too small or empty: {len(audio_data) if audio_data else 0} bytes")
                return False

            logger.debug(f"Playing audio: {len(audio_data)} bytes")

            # Create temp file and ensure it's fully written
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_data)
                f.flush()  # Ensure data is written to disk
                os.fsync(f.fileno())  # Force write to disk
                temp_path = f.name

            logger.debug(f"Audio written to: {temp_path}")

            # Small delay to ensure file is fully written
            time.sleep(0.1)

            # Play using system audio player
            system = platform.system()
            try:
                if system == "Linux":
                    import subprocess

                    # Use subprocess with explicit wait and no output capture
                    result = subprocess.run(
                        ["aplay", "-q", temp_path],
                        check=True,
                        timeout=10,  # Add timeout
                    )
                    logger.debug("aplay completed successfully")

                elif system == "Darwin":  # macOS
                    import subprocess

                    result = subprocess.run(
                        ["afplay", temp_path],
                        check=True,
                        timeout=10,  # Add timeout
                    )
                    logger.debug("afplay completed successfully")

                elif system == "Windows":
                    import subprocess

                    result = subprocess.run(
                        ["powershell", "-c", f"(New-Object Media.SoundPlayer '{temp_path}').PlaySync()"],
                        check=True,
                        timeout=10,  # Add timeout
                    )
                    logger.debug("Windows audio player completed successfully")

            except subprocess.TimeoutExpired:
                logger.error("Audio playback timed out")
                Path(temp_path).unlink(missing_ok=True)
                return False

            # Small delay to ensure playback completes
            time.sleep(0.1)

            # Clean up temp file
            Path(temp_path).unlink(missing_ok=True)

            logger.debug("Audio playback completed successfully")
            return True

        except FileNotFoundError:
            logger.error(f"Audio player not found for system: {platform.system()}")
            return False
        except Exception as e:
            logger.error(f"Audio playback failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False

    def _get_cache_key(self, text: str) -> str:
        """
        Generate cache key from text.

        Args:
            text: Text to cache

        Returns:
            MD5 hash of text as cache key
        """
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def _get_cached_audio(self, text: str) -> Optional[bytes]:
        """
        Get cached audio for text if available.

        Args:
            text: Text to look up

        Returns:
            Cached audio bytes, or None if not found
        """
        cache_key = self._get_cache_key(text)
        cache_file = Path(self.config.cache_dir) / f"{cache_key}.wav"

        if cache_file.exists():
            # Check if cache is still valid
            file_age = datetime.now().timestamp() - cache_file.stat().st_mtime
            if file_age < self.config.cache_ttl_seconds:
                try:
                    return cache_file.read_bytes()
                except Exception as e:
                    logger.warning(f"Failed to read cache file: {e}")

        return None

    def _cache_audio(self, text: str, audio_data: bytes) -> None:
        """
        Cache audio data for text.

        Args:
            text: Text that was synthesized
            audio_data: Audio bytes to cache
        """
        cache_key = self._get_cache_key(text)
        cache_file = Path(self.config.cache_dir) / f"{cache_key}.wav"

        try:
            cache_file.write_bytes(audio_data)
            logger.debug(f"Cached audio for: {text[:50]}...")
        except Exception as e:
            logger.warning(f"Failed to cache audio: {e}")

    def _generate_assessment_feedback(
        self, result: speechsdk.PronunciationAssessmentResult
    ) -> str:
        """
        Generate human-readable feedback from assessment result.

        Args:
            result: Azure pronunciation assessment result

        Returns:
            Feedback message
        """
        # Calculate overall score
        accuracy = result.accuracy_score
        fluency = result.fluency_score
        completeness = result.completeness_score

        if accuracy >= 90 and fluency >= 80:
            return "Excellent pronunciation! Very natural and accurate."
        elif accuracy >= 80:
            return "Good pronunciation! Minor improvements in accuracy would make it even better."
        elif accuracy >= 70:
            return "Fair pronunciation. Focus on individual sounds and try to speak more smoothly."
        elif accuracy >= 60:
            return "Developing pronunciation. Listen carefully to the example and practice each sound."
        else:
            return "Keep practicing! Focus on mimicking the sounds in the example recording."

    def clear_cache(self) -> int:
        """
        Clear all cached audio files.

        Returns:
            Number of cache files removed
        """
        cache_path = Path(self.config.cache_dir)
        if not cache_path.exists():
            return 0

        count = 0
        for file in cache_path.glob("*.wav"):
            try:
                file.unlink()
                count += 1
            except Exception as e:
                logger.warning(f"Failed to delete cache file {file}: {e}")

        logger.info(f"Cleared {count} cached audio files")
        return count
