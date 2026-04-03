"""
Speech module for Azure Speech Service integration.

This module provides text-to-speech, speech recognition, and pronunciation
assessment capabilities using Microsoft Azure's Cognitive Services.
"""

from .client import AzureSpeechClient
from .config import SpeechConfig
from .models import AudioRecording, PronunciationAssessmentResult

__all__ = ["AzureSpeechClient", "SpeechConfig", "AudioRecording", "PronunciationAssessmentResult"]
