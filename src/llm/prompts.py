"""
Prompt templates and builders for different teaching scenarios.
"""

from typing import Any, Dict, Optional


class PromptTemplate:
    """Base class for prompt templates."""

    def build(self, **kwargs) -> str:
        """Build the prompt with given parameters."""
        raise NotImplementedError


class ConversationPrompt(PromptTemplate):
    """Prompt for natural conversation practice."""

    def build(
        self,
        target_language: str,
        learner_level: str,
        topic: Optional[str] = None,
        vocabulary_to_use: Optional[list[str]] = None,
    ) -> str:
        """Build a conversation prompt."""
        prompt = f"""You are an adaptive {target_language} language learning companion.

The learner is at {learner_level} level."""

        if topic:
            prompt += f"\nThe conversation topic is: {topic}"

        if vocabulary_to_use:
            prompt += f"\nTry to naturally incorporate these words/phrases: {', '.join(vocabulary_to_use)}"

        prompt += """

Your approach:
- Keep conversations natural and engaging
- Adjust complexity based on learner responses
- Be patient and encouraging
- Model correct grammar and vocabulary
- Ask follow-up questions to keep conversation flowing
- Occasionally introduce new words or structures in context

Respond in {target_language} unless a brief English explanation is necessary for clarity.
""".format(target_language=target_language)

        return prompt


class ErrorAnalysisPrompt(PromptTemplate):
    """Prompt for analyzing learner errors."""

    def build(
        self,
        target_language: str,
        learner_level: str,
        focus_areas: Optional[list[str]] = None,
    ) -> str:
        """Build an error analysis prompt."""
        prompt = f"""Analyze this {target_language} learner's input for errors.

Learner level: {learner_level}"""

        if focus_areas:
            prompt += f"\nFocus on these areas: {', '.join(focus_areas)}"

        prompt += """

For each error found, provide:
1. Type: grammar, vocabulary, word order, etc.
2. Severity: minor (small mistake), moderate (affects clarity), major (impedes understanding)
3. Description: What went wrong
4. Correction: The correct form
5. Critical: true if this is a fundamental error that needs immediate attention

Return ONLY a JSON object following this structure:
{
    "errors": [
        {
            "type": "grammar",
            "severity": "moderate",
            "description": "Verb should be second position",
            "correction": "Ich gehe heute ins Kino",
            "critical": true
        }
    ]
}"""

        return prompt


class IntroductionPrompt(PromptTemplate):
    """Prompt for introducing new material."""

    def build(
        self,
        material_type: str,  # "vocabulary" or "grammar"
        target_language: str,
        learner_level: str,
        context: str,
    ) -> str:
        """Build a prompt for introducing new material."""
        prompt = f"""Introduce new {material_type} to a {target_language} learner at {learner_level} level.

Context: {context}

Your approach:
- Introduce the material naturally in conversation
- Provide clear examples
- Check for understanding
- Make it relevant to the conversation
- Don't overwhelm - 1-3 new items maximum
- Be encouraging and supportive"""

        return prompt


class ExplicitGrammarLessonPrompt(PromptTemplate):
    """Prompt for explicit grammar instruction with structured explanations."""

    def build(
        self,
        target_language: str,
        learner_level: str,
        grammar_pattern: str,
        pattern_description: str,
        examples: list[str],
        context: str,
    ) -> str:
        """Build a prompt for explicit grammar instruction."""
        examples_text = "\n".join(f"- {ex}" for ex in examples)

        prompt = f"""You are teaching a {target_language} learner at {learner_level} level.

GRAMMAR FOCUS: {grammar_pattern}
PATTERN: {pattern_description}

EXAMPLES TO SHOW:
{examples_text}

CONVERSATION CONTEXT: {context}

IMPORTANT: This is an EXPLICIT GRAMMAR LESSON moment. Pause the natural conversation flow to provide focused instruction.

Your response should:
1. **Acknowledge the conversation briefly**, then transition to explicit teaching
2. **Explain the grammar pattern clearly** - what it is, when to use it, why it matters
3. **Show the examples** with clear breakdowns of how they work
4. **Connect it to the conversation context** so it feels relevant
5. **Give the learner a chance to try it** - prompt them to use the pattern
6. **Be encouraging but direct** - this is instruction time, not just casual chat

Use English for the grammar explanation and pattern breakdown, then switch to {target_language} for examples and practice.

Example structure:
"Great question! Let me explain [pattern] clearly. In {target_language}, [explanation]. Here's how it works: [breakdown]. Your turn - can you [practice prompt]?"

Keep it structured and educational while remaining warm and supportive."""

        return prompt


class PromptBuilder:
    """
    Builds complete prompts combining system prompts and context.

    This orchestrates different prompt templates and adds dynamic context
    for generating pedagogically appropriate responses.
    """

    def __init__(self, target_language: str = "german"):
        self.target_language = target_language
        self.conversation_template = ConversationPrompt()
        self.error_template = ErrorAnalysisPrompt()
        self.introduction_template = IntroductionPrompt()
        self.explicit_grammar_template = ExplicitGrammarLessonPrompt()

    def build_conversation_prompt(
        self,
        learner_level: str,
        topic: Optional[str] = None,
        vocabulary_to_use: Optional[list[str]] = None,
        strategy: Optional[str] = None,
    ) -> str:
        """Build a complete conversation prompt."""
        prompt = self.conversation_template.build(
            target_language=self.target_language,
            learner_level=learner_level,
            topic=topic,
            vocabulary_to_use=vocabulary_to_use,
        )

        if strategy:
            prompt += f"\n\nTeaching strategy: {strategy}"

        return prompt

    def build_correction_prompt(
        self,
        error: dict,
        learner_input: str,
        correction_strategy: str,
        learner_level: str,
    ) -> str:
        """Build a prompt for error correction."""

        strategy_prompts = {
            "immediate": f"""The learner made this error: {error.get('description', '')}

Correct version: {error.get('correction', '')}

Provide a gentle, clear explanation in the conversation. Be encouraging and show why this is important.""",
            "gentle_recast": f"""The learner said: "{learner_input}"

Without explicitly pointing out errors, model the correct way to say this. Incorporate your response naturally into the conversation.""",
            "self_correction": f"""The learner said: "{learner_input}"

There's an error. Hint at what might be wrong and give them a chance to notice and correct it themselves. Don't just give the answer.""",
        }

        base = f"""You are helping a {learner_level} {self.target_language} learner.\n\n"""
        strategy_text = strategy_prompts.get(
            correction_strategy,
            "Help the learner improve naturally.",
        )

        return base + strategy_text

    def build_introduction_prompt(
        self,
        material_type: str,
        items: list[Any],
        context: str,
        learner_level: str,
    ) -> str:
        """Build a prompt for introducing new material."""

        items_text = ""
        if material_type == "vocabulary":
            items_text = ", ".join(getattr(item, "word", str(item)) for item in items)
        elif material_type == "grammar":
            items_text = ", ".join(getattr(item, "name", str(item)) for item in items)

        return self.introduction_template.build(
            material_type=material_type,
            target_language=self.target_language,
            learner_level=learner_level,
            context=f"{context}. Items to introduce: {items_text}",
        )
