"""
Configuration for Azure Speech Service.

This module handles loading and managing configuration for Azure Speech Service
from environment variables.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass
class SpeechConfig:
    """
    Configuration for Azure Speech Service.

    Attributes:
        speech_key: Azure Speech Service subscription key
        speech_region: Azure region (e.g., eastus, westeurope)
        voice_name: Neural TTS voice name for German
        enable_cache: Whether to cache synthesized speech
        cache_dir: Directory for audio cache
        cache_ttl_seconds: How long to keep cached audio (default: 30 days)
    """

    speech_key: str
    speech_region: str
    voice_name: str = "de-DE-KatjaNeural"  # German female voice
    enable_cache: bool = True
    cache_dir: str = "data/audio_cache"
    cache_ttl_seconds: int = 30 * 24 * 60 * 60  # 30 days

    @classmethod
    def from_env(cls) -> Optional["SpeechConfig"]:
        """
        Load configuration from environment variables.

        Checks for AZURE_SPEECH_KEY/SPEECH_KEY and AZURE_SPEECH_REGION/SPEECH_REGION.

        Returns:
            SpeechConfig if credentials found, None otherwise
        """
        load_dotenv()

        key = os.getenv("AZURE_SPEECH_KEY") or os.getenv("SPEECH_KEY")
        region = os.getenv("AZURE_SPEECH_REGION") or os.getenv("SPEECH_REGION")

        if not key or not region:
            return None

        return cls(speech_key=key, speech_region=region)

    def ensure_cache_dir(self) -> Path:
        """
        Ensure cache directory exists, create if needed.

        Returns:
            Path to cache directory
        """
        cache_path = Path(self.cache_dir)
        cache_path.mkdir(parents=True, exist_ok=True)
        return cache_path

    @property
    def is_configured(self) -> bool:
        """Check if configuration has valid credentials."""
        return bool(self.speech_key and self.speech_region)
