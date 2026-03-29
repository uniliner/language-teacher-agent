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
        recent_learner_inputs: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze learner input for errors and learning opportunities.

        Args:
            learner_input: What the learner said/wrote
            target_language: Language being learned (e.g., "german")
            learner_level: CEFR level (A1, A2, B1, etc.)
            valid_grammar_patterns: Optional list of valid pattern names for grammar errors.
                If provided, grammar errors must include a "pattern" field using one of these names.
            recent_learner_inputs: Optional list of recent learner inputs for detecting recurring errors.

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

        # Build recent inputs context for recurring error detection
        recent_context = ""
        if recent_learner_inputs:
            recent_inputs_text = "\n".join(f"- {inp}" for inp in recent_learner_inputs[-5:])
            recent_context = f"""

RECENT LEARNER INPUTS (for detecting recurring errors):
{recent_inputs_text}

Set "recurring": true ONLY if an error of the same TYPE (e.g., verb position, word order) and PATTERN has appeared
in the recent inputs above. Match based on the grammatical pattern, not the specific words used.
"""

        system_prompt = f"""You are an expert language teacher analyzing a {target_language} learner's input.
The learner is at {learner_level} level.

CRITICAL ERROR DETECTION RULES:
1. ONLY flag errors that are OBJECTIVELY GRAMMATICALLY WRONG
2. Do NOT flag stylistic preferences, word choice suggestions, or minor variations that are still grammatically correct
3. Examples of what NOT to flag:
   - Correct word order even if there's a more common alternative (e.g., "obwohl ich Müsli auch mag" is CORRECT)
   - Vocabulary choices that are grammatically correct but less common (e.g., "zu schwarz" is not an error)
   - Regional variations that are still grammatically valid
4. Each error entry MUST focus on a SINGLE, SPECIFIC error type:
   - Do NOT mix grammar and vocabulary issues in the same error object
   - If there are multiple issues, create separate error entries for each
   - Keep "type" field consistent with the PRIMARY error in that entry

Analyze the input for:
1. OBJECTIVE grammar errors only (specify severity: minor, moderate, major)
2. Vocabulary usage (important words the learner used or tried to use)
3. Naturalness (is it natural or awkward?)
4. What the learner is trying to say{pattern_instruction}{recent_context}

Return a JSON object with this structure:
{{
    "errors": [
        {{
            "type": "grammar|vocabulary",
            "severity": "minor|moderate|major",
            "description": "brief explanation",
            "correction": "corrected version",
            "critical": false{', "pattern": "sv_order_main_clause"  // REQUIRED for grammar errors - use only valid pattern names from list above' if valid_grammar_patterns else ''},
            "recurring": false  // true if this same error type and pattern appeared in recent inputs
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
        from pedagogy.strategies import TeachingStrategy

        # Check if this is an explicit grammar lesson moment
        is_explicit_grammar = (
            decision.action in ["introduce", "review"]
            and decision.metadata.get("introduction_type") == "grammar"
            or decision.metadata.get("review_type") == "grammar"
        ) and decision.strategy in [
            TeachingStrategy.Explicit_explanation,
            TeachingStrategy.Pattern_highlighting,
        ]

        if is_explicit_grammar:
            # Use explicit grammar lesson prompt
            return self._generate_explicit_grammar_response(
                learner_input=learner_input,
                decision=decision,
                conversation_context=conversation_context,
                target_language=target_language,
            )

        # Default: Build system prompt based on decision
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

    def _generate_explicit_grammar_response(
        self,
        learner_input: str,
        decision: object,
        conversation_context: Dict[str, Any],
        target_language: str,
    ) -> str:
        """Generate an explicit grammar lesson response."""
        from pedagogy.strategies import TeachingStrategy

        # Extract grammar pattern information
        metadata = decision.metadata
        grammar_pattern = metadata.get("grammar_pattern", "")
        pattern_description = metadata.get("pattern_description", "")

        # For review, get pattern info from metadata
        if not grammar_pattern and metadata.get("patterns"):
            grammar_pattern = metadata["patterns"][0]
            pattern_descriptions = metadata.get("pattern_descriptions", [])
            if pattern_descriptions:
                pattern_description = pattern_descriptions[0]

        # Build explicit grammar prompt
        strategy_guidance = self._get_strategy_guidance(decision.strategy)

        system_prompt = f"""You are an adaptive {target_language} language learning companion.

Current teaching approach: {strategy_guidance}

Learner context:
- Confidence level: {conversation_context.get('confidence', 'moderate')}
- Recent error rate: {conversation_context.get('error_rate', 0.0):.1%}
- CEFR level: {conversation_context.get('cefr_level', 'A1')}

IMPORTANT: This is an EXPLICIT GRAMMAR LESSON moment. Pause the natural conversation flow to provide focused instruction.

Your response should:
1. **Acknowledge the conversation briefly**, then transition to explicit teaching
2. **Explain the grammar pattern clearly** - what it is, when to use it, why it matters
3. **Show clear examples** with breakdowns of how they work
4. **Connect it to the conversation context** so it feels relevant
5. **Give the learner a chance to try it** - prompt them to use the pattern
6. **Be encouraging but direct** - this is instruction time, not just casual chat

Use English for the grammar explanation and pattern breakdown, then switch to {target_language} for examples and practice."""

        # Build user message with grammar context
        user_message = f"Learner said: {learner_input}\n\n"

        if grammar_pattern:
            user_message += f"GRAMMAR PATTERN: {grammar_pattern}\n"
        if pattern_description:
            user_message += f"PATTERN DESCRIPTION: {pattern_description}\n"

        if decision.action == "introduce":
            user_message += f"\nACTION: Introduce this grammar pattern explicitly\n"
        elif decision.action == "review":
            mastery_scores = metadata.get("mastery_scores", [])
            if mastery_scores:
                user_message += f"\nACTION: Review this grammar pattern (current mastery: {mastery_scores[0]:.0%})\n"
            else:
                user_message += f"\nACTION: Review this grammar pattern\n"

        user_message += "\nGenerate your explicit grammar lesson response:"

        response = self.client.messages.create(
            model=self.model,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            temperature=0.7,  # Slightly lower for structured instruction
            max_tokens=800,  # Allow more tokens for explanations
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
            TeachingStrategy.Explicit_explanation: "PAUSE THE CONVERSATION FLOW. Deliver a focused, structured grammar lesson with explicit explanations, clear examples, and breakdowns. This is teaching time, not casual chat.",
            TeachingStrategy.Pattern_highlighting: "Draw explicit attention to a specific grammar pattern. Show how it works, give clear examples, and explain when to use it. Be direct and instructional.",
            TeachingStrategy.Contextual_introduction: "Introduce new material naturally within the conversation flow. Weave it into context without breaking the conversational rhythm.",
            TeachingStrategy.PRONUNCIATION_TEACHING: "PAUSE THE CONVERSATION FLOW. Provide a focused pronunciation tip. Explain how to produce the sound clearly, give practical tips, and encourage practice. Keep it brief (2-3 sentences) and actionable. End by asking them to try pronouncing a practice word.",
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
