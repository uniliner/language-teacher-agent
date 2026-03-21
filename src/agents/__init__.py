"""Agent implementations for different teaching roles."""

from .base import Agent, AgentConfig
from .conversation import ConversationAgent
from .grammar_curriculum import GrammarCurriculumAgent

__all__ = ["Agent", "AgentConfig", "ConversationAgent", "GrammarCurriculumAgent"]
