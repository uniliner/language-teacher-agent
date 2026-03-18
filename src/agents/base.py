"""
Base agent class.

All specialized agents inherit from this. Provides common functionality
and defines the interface that all agents must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional

from models.learner import Learner
from llm.client import LLMClient


@dataclass
class AgentConfig:
    """Configuration for an agent."""

    name: str
    description: str
    target_language: str = "german"
    temperature: float = 0.7
    max_tokens: int = 500


class Agent(ABC):
    """
    Abstract base class for all agents.

    Agents are specialized components that handle specific aspects
    of language learning (conversation, pronunciation, grammar, etc.).

    The multi-agent architecture allows for:
- Specialized expertise per agent
- Independent evolution of capabilities
- Easy addition of new agent types
- Parallel operation when needed
    """

    def __init__(
        self,
        config: AgentConfig,
        learner: Learner,
        llm_client: Optional[LLMClient] = None,
    ):
        """
        Initialize the agent.

        Args:
            config: Agent configuration
            learner: Learner state
            llm_client: LLM client for AI interactions
        """
        self.config = config
        self.learner = learner
        self.llm_client = llm_client

    @abstractmethod
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process input and return response.

        This is the main method that each agent must implement.
        It takes input (learner speech/text, etc.) and returns
        a response with teaching actions.

        Args:
            input_data: Input data from learner or system

        Returns:
            Response dictionary with agent-specific results
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> list[str]:
        """
        Return list of what this agent can do.

        Returns:
            List of capability descriptions
        """
        pass

    def update_learner_state(self, updates: Dict[str, Any]) -> None:
        """
        Update learner state based on interaction.

        Args:
            updates: Dictionary of fields to update
        """
        for key, value in updates.items():
            if hasattr(self.learner, key):
                setattr(self.learner, key, value)

        self.learner.last_updated = self.learner.last_updated

    def get_status(self) -> Dict[str, Any]:
        """
        Get agent status and state.

        Returns:
            Dictionary with agent status information
        """
        return {
            "name": self.config.name,
            "description": self.config.description,
            "target_language": self.config.target_language,
            "capabilities": self.get_capabilities(),
            "learner_id": self.learner.learner_id,
        }
