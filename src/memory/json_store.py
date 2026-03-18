"""
JSON-based memory store implementation.

Simple file-based storage suitable for single-user applications.
Each learner's data is stored in a separate JSON file.
"""

import json
import os
from pathlib import Path
from typing import Optional

from models.learner import Learner
from memory.store import MemoryStore


class JSONMemoryStore(MemoryStore):
    """
    JSON file-based memory store.

    Stores each learner's state as a JSON file in the data directory.
    Simple and portable, suitable for development and single-user setups.
    """

    def __init__(self, data_dir: str = "./data"):
        """
        Initialize the JSON store.

        Args:
            data_dir: Directory to store learner data files
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _get_learner_path(self, learner_id: str) -> Path:
        """Get the file path for a learner."""
        return self.data_dir / f"{learner_id}.json"

    def save_learner(self, learner: Learner) -> None:
        """
        Save learner state to JSON file.

        Args:
            learner: Learner object to save
        """
        learner_path = self._get_learner_path(learner.learner_id)

        # Convert to dict for JSON serialization
        learner_dict = learner.model_dump(mode="json")

        # Handle datetime serialization
        def json_serializer(obj):
            """Handle datetime and other non-serializable objects."""
            if hasattr(obj, "isoformat"):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        # Write to file with atomic write (temp file + rename)
        temp_path = learner_path.with_suffix(".json.tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(learner_dict, f, indent=2, default=json_serializer, ensure_ascii=False)

            # Atomic rename
            temp_path.replace(learner_path)
        except Exception as e:
            # Clean up temp file if something went wrong
            if temp_path.exists():
                temp_path.unlink()
            raise IOError(f"Failed to save learner data: {e}")

    def load_learner(self, learner_id: str) -> Optional[Learner]:
        """
        Load learner state from JSON file.

        Args:
            learner_id: ID of learner to load

        Returns:
            Learner object if found, None otherwise
        """
        learner_path = self._get_learner_path(learner_id)

        if not learner_path.exists():
            return None

        try:
            with open(learner_path, "r", encoding="utf-8") as f:
                learner_dict = json.load(f)

            # Reconstruct Learner object
            return Learner(**learner_dict)
        except Exception as e:
            raise IOError(f"Failed to load learner data: {e}")

    def learner_exists(self, learner_id: str) -> bool:
        """
        Check if learner data exists.

        Args:
            learner_id: ID of learner to check

        Returns:
            True if learner data file exists
        """
        return self._get_learner_path(learner_id).exists()

    def delete_learner(self, learner_id: str) -> None:
        """
        Delete learner data.

        Args:
            learner_id: ID of learner to delete
        """
        learner_path = self._get_learner_path(learner_id)

        if learner_path.exists():
            learner_path.unlink()

    def list_learners(self) -> list[str]:
        """
        List all learner IDs.

        Returns:
            List of learner IDs found in data directory
        """
        if not self.data_dir.exists():
            return []

        learners = []
        for file_path in self.data_dir.glob("*.json"):
            # Skip temp files
            if not file_path.name.endswith(".tmp"):
                learners.append(file_path.stem)  # filename without .json

        return sorted(learners)

    def backup_learner(self, learner_id: str, backup_suffix: str = "bak") -> bool:
        """
        Create a backup of learner data.

        Args:
            learner_id: ID of learner to backup
            backup_suffix: Suffix for backup file

        Returns:
            True if backup successful
        """
        learner_path = self._get_learner_path(learner_id)

        if not learner_path.exists():
            return False

        backup_path = learner_path.with_suffix(f".json.{backup_suffix}")

        try:
            import shutil
            shutil.copy2(learner_path, backup_path)
            return True
        except Exception:
            return False

    def get_learner_backup_count(self, learner_id: str) -> int:
        """Get number of backups for a learner."""
        pattern = f"{learner_id}.json.*"
        backups = list(self.data_dir.glob(pattern))
        return len(backups)
