"""
Data models for speech functionality.

This module defines the data structures used throughout the speech module
for audio recordings and pronunciation assessment results.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class AudioRecording:
    """
    Represents a recorded audio clip.

    Attributes:
        audio_data: Raw audio bytes (WAV format)
        duration_ms: Duration of recording in milliseconds
        timestamp: When the recording was made
        pattern_id: Optional pronunciation pattern being practiced
        target_text: The text the user was trying to say
    """

    audio_data: bytes
    duration_ms: int
    timestamp: datetime
    pattern_id: Optional[str] = None
    target_text: Optional[str] = None

    @property
    def duration_seconds(self) -> float:
        """Get duration in seconds."""
        return self.duration_ms / 1000.0


@dataclass
class PronunciationAssessmentResult:
    """
    Results from pronunciation assessment using Azure Speech Service.

    Attributes:
        accuracy_score: Overall pronunciation accuracy (0.0 to 1.0)
        fluency_score: Fluency and smoothness (0.0 to 1.0)
        completeness_score: How much of the target was spoken (0.0 to 1.0)
        prosody_score: Intonation and stress patterns (0.0 to 1.0)
        error_text: Transcription of what was actually heard
        feedback: Human-readable feedback summary
    """

    accuracy_score: float
    fluency_score: float
    completeness_score: float
    prosody_score: float
    error_text: Optional[str] = None
    feedback: str = ""

    @property
    def overall_score(self) -> float:
        """
        Calculate overall score as average of all components.

        Returns:
            Average score from 0.0 to 1.0
        """
        return (
            self.accuracy_score
            + self.fluency_score
            + self.completeness_score
            + self.prosody_score
        ) / 4.0

    def get_feedback_grade(self) -> str:
        """
        Get a letter grade based on overall score.

        Returns:
            Letter grade (A, B, C, D, F)
        """
        score = self.overall_score
        if score >= 0.9:
            return "A"
        elif score >= 0.8:
            return "B"
        elif score >= 0.7:
            return "C"
        elif score >= 0.6:
            return "D"
        else:
            return "F"

    def get_feedback_message(self) -> str:
        """
        Get encouraging feedback message based on performance.

        Returns:
            Personalized feedback message
        """
        grade = self.get_feedback_grade()
        score = self.overall_score

        if grade == "A":
            return "🌟 Excellent! Your pronunciation is nearly perfect!"
        elif grade == "B":
            return "👏 Great job! Very good pronunciation with minor improvements possible."
        elif grade == "C":
            return "👍 Good effort! Your pronunciation is understandable. Keep practicing!"
        elif grade == "D":
            return "💪 Nice try! Focus on the specific sounds mentioned in the feedback."
        else:
            return "🎯 Keep practicing! Listen to the example again and try to mimic the sounds."

    def to_dict(self) -> dict:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary representation of assessment results
        """
        return {
            "accuracy_score": self.accuracy_score,
            "fluency_score": self.fluency_score,
            "completeness_score": self.completeness_score,
            "prosody_score": self.prosody_score,
            "overall_score": self.overall_score,
            "grade": self.get_feedback_grade(),
            "error_text": self.error_text,
            "feedback": self.feedback,
        }
