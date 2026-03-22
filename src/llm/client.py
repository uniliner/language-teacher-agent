"""
LLM client using Anthropic's Claude API.

This handles communication with Claude for natural conversation generation,
error detection, and pedagogical responses.
"""

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from anthropic import Anthropic


@dataclass
class Message:
    """A message in the conversation."""

    role: str  # "user", "assistant", "system"
    content: str
    metadata: Optional[Dict[str, Any]] = None


class LLMClient:
    """
    Client for interacting with Claude API.

    Handles conversation generation, error detection, and response formatting
    specifically designed for language learning contexts.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize the LLM client.

        Args:
            api_key: Anthropic API key (reads from env if not provided)
            model: Model identifier to use
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not found. Set it in environment or pass to constructor."
            )

        self.client = Anthropic(api_key=self.api_key)
        self.model = model
        self.conversation_history: List[Message] = []

    def generate_response(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[List[Message]] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> str:
        """
        Generate a response from Claude.

        Args:
            system_prompt: System prompt to guide behavior
            user_message: Current user message
            conversation_history: Previous messages for context
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens in response

        Returns:
            Generated response text
        """
        messages = []

        # Add conversation history
        if conversation_history:
            for msg in conversation_history[-10:]:  # Last 10 messages for context
                if msg.role in ["user", "assistant"]:
                    messages.append({"role": msg.role, "content": msg.content})

        # Add current message
        messages.append({"role": "user", "content": user_message})

        response = self.client.messages.create(
            model=self.model,
            system=system_prompt,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return response.content[0].text

    def analyze_learner_input(
        self,
        learner_input: str,
        target_language: str,
        learner_level: str,
        valid_grammar_patterns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze learner input for errors and learning opportunities.

        Args:
            learner_input: What the learner said/wrote
            target_language: Language being learned (e.g., "german")
            learner_level: CEFR level (A1, A2, B1, etc.)
            valid_grammar_patterns: Optional list of valid pattern names for grammar errors.
                If provided, grammar errors must include a "pattern" field using one of these names.

        Returns:
            Dictionary with analysis results including errors and suggestions
        """
        # Build system prompt with optional pattern guidance
        pattern_instruction = ""
        if valid_grammar_patterns:
            patterns_str = ", ".join(valid_grammar_patterns)
            pattern_instruction = f"""

IMPORTANT: For each grammar error, you MUST identify the specific grammar pattern from the curriculum.
Valid pattern names are:
{patterns_str}

Choose the MOST SPECIFIC pattern that applies to the error. If you're unsure which pattern to choose,
pick the one that best describes the grammatical structure the learner is struggling with.
"""

        system_prompt = f"""You are an expert language teacher analyzing a {target_language} learner's input.
The learner is at {learner_level} level.

Analyze the input for:
1. Grammar errors (specify severity: minor, moderate, major)
2. Vocabulary usage (important words the learner used or tried to use)
3. Naturalness (is it natural or awkward?)
4. What the learner is trying to say{pattern_instruction}

Return a JSON object with this structure:
{{
    "errors": [
        {{
            "type": "grammar|vocabulary",
            "severity": "minor|moderate|major",
            "description": "brief explanation",
            "correction": "corrected version",
            "critical": false{', "pattern": "sv_order_main_clause"  // REQUIRED for grammar errors - use only valid pattern names from list above' if valid_grammar_patterns else ''}
        }}
    ],
    "vocabulary_used": [
        {{"word": "german_word", "translation": "english_translation", "part_of_speech": "noun|verb|adjective|adverb|preposition|pronoun|other"}}
    ],
    "intended_meaning": "what they're trying to say",
    "naturalness": "natural|awkward",
    "confidence_level": "high|medium|low"
}}"""

        response = self.client.messages.create(
            model=self.model,
            system=system_prompt,
            messages=[{"role": "user", "content": learner_input}],
            temperature=0.3,  # Lower temp for analysis
            max_tokens=800,
        )

        import json

        try:
            # Extract JSON from response
            response_text = response.content[0].text
            # Handle markdown code blocks if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            return json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                "errors": [],
                "vocabulary_used": [],
                "intended_meaning": learner_input,
                "naturalness": "unknown",
                "confidence_level": "medium"
            }

    def generate_teaching_response(
        self,
        learner_input: str,
        decision: object,  # TeachingDecision
        conversation_context: Dict[str, Any],
        target_language: str,
    ) -> str:
        """
        Generate a pedagogically-informed response.

        Args:
            learner_input: What the learner said
            decision: TeachingDecision from pedagogical engine
            conversation_context: Current conversation state
            target_language: Language being learned

        Returns:
            Generated response in target language
        """
        # Build system prompt based on decision
        strategy_guidance = self._get_strategy_guidance(decision.strategy)

        system_prompt = f"""You are an adaptive {target_language} language learning companion.
Your goal is to conduct natural conversations while helping the learner improve.

Current teaching approach: {strategy_guidance}

Learner context:
- Confidence level: {conversation_context.get('confidence', 'moderate')}
- Recent error rate: {conversation_context.get('error_rate', 0.0):.1%}
- CEFR level: {conversation_context.get('cefr_level', 'A1')}

Guidelines:
1. Respond in {target_language} most of the time
2. Use English only for brief explanations when necessary
3. Be encouraging and supportive
4. Follow the teaching approach specified above
5. Keep responses natural and conversational
6. Don't lecture - guide through conversation"""

        # Build user message with context
        user_message = f"Learner said: {learner_input}\n\n"

        if decision.action == "correct" and decision.metadata.get("error"):
            error = decision.metadata["error"]
            user_message += f"Error to address: {error}\n"

        user_message += "\nGenerate your response:"

        response = self.client.messages.create(
            model=self.model,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            temperature=0.8,  # Higher temp for natural conversation
            max_tokens=600,
        )

        return response.content[0].text

    def _get_strategy_guidance(self, strategy) -> str:
        """Get guidance text for a teaching strategy."""
        from pedagogy.strategies import TeachingStrategy

        guidance_map = {
            TeachingStrategy.IMMEDIATE_CORRECTION: "Gently but explicitly correct the error. Show the correct form and briefly explain why.",
            TeachingStrategy.DELAYED_CORRECTION: "Note the error for later but continue the conversation naturally. Don't explicitly correct right now.",
            TeachingStrategy.GENTLE_RECAST: "Reformulate what they said correctly without drawing attention to the error. Just model the correct form.",
            TeachingStrategy.PROMPT_SELF_CORRECTION: "Hint that there's an error and give them a chance to self-correct.",
            TeachingStrategy.FLOW_PRESERVATION: "Prioritize keeping the conversation flowing. Don't correct minor errors.",
            TeachingStrategy.CONFIDENCE_BUILDING: "Focus on what they did well. Be encouraging. Avoid corrections unless necessary for communication.",
            TeachingStrategy.CHALLENGE_PROVIDING: "Gently push them beyond their comfort. Introduce slightly more complex structures or vocabulary.",
            TeachingStrategy.Scaffolding: "Build on what they already know. Connect new material to familiar structures.",
            TeachingStrategy.SPACED_REPETITION: "Gently incorporate previously learned material that needs review into the conversation.",
        }

        return guidance_map.get(strategy, "Converse naturally while being helpful and encouraging.")

    def add_to_history(self, message: Message) -> None:
        """Add a message to conversation history."""
        self.conversation_history.append(message)

        # Keep history manageable
        if len(self.conversation_history) > 50:
            self.conversation_history = self.conversation_history[-25:]

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history = []
