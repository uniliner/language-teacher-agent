"""Agent implementations for different teaching roles."""

from .base import Agent, AgentConfig
from .conversation import ConversationAgent

__all__ = ["Agent", "AgentConfig", "ConversationAgent"]
