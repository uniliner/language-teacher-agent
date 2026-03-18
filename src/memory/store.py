"""
Abstract interface for memory storage.

This allows for different storage backends (JSON, SQLite, Redis, etc.)
to be swapped out without changing the core application.
"""

from abc import ABC, abstractmethod
from typing import Optional

from models.learner import Learner


class MemoryStore(ABC):
    """Abstract base class for memory storage."""

    @abstractmethod
    def save_learner(self, learner: Learner) -> None:
        """Save learner state."""
        pass

    @abstractmethod
    def load_learner(self, learner_id: str) -> Optional[Learner]:
        """Load learner state by ID."""
        pass

    @abstractmethod
    def learner_exists(self, learner_id: str) -> bool:
        """Check if learner data exists."""
        pass

    @abstractmethod
    def delete_learner(self, learner_id: str) -> None:
        """Delete learner data."""
        pass

    @abstractmethod
    def list_learners(self) -> list[str]:
        """List all learner IDs."""
        pass
