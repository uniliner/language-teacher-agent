"""
Prompt definitions and versioning for GrammarCurriculumAgent LLM calls.

This module centralizes all prompts used by the GrammarCurriculumAgent to enable:
- Version tracking for regression testing
- Consistent prompt formatting across the codebase
- Easy prompt iteration and A/B testing
"""

# Version tracking for regression debugging
# Increment this when prompts change significantly to track effectiveness
PROMPT_VERSION = "v1.0"

# ============================================================================
# TEACHING DECISION PROMPTS
# ============================================================================

TEACHING_DECISION_SYSTEM_PROMPT = """You are a German grammar pedagogy expert. Always respond with valid JSON only, no additional text."""

TEACHING_DECISION_USER_PROMPT_TEMPLATE = """You are a pedagogical grammar expert. Decide what grammar teaching action to take.

Learner State:
- Level: {cefr_level}
- Confidence: {confidence}
- Recent errors: {recent_errors}
- Mastered patterns: {mastered_patterns}
- Current weaknesses: {weaknesses}

Conversation Context:
- Topic: {topic}
- Flow score: {flow_score} (0.0 = struggling, 1.0 = flowing)
- Recent learner input: {learner_input}

Available Actions:
1. "introduce_pattern" - Teach a new grammar pattern
2. "review_pattern" - Practice a pattern due for review
3. "reinforce_pattern" - Strengthen a weak pattern
4. "wait" - Don't interrupt conversation flow

IMPORTANT: Return ONLY valid JSON in this exact format:
{{
    "action": "introduce_pattern" | "review_pattern" | "reinforce_pattern" | "wait",
    "pattern": "pattern_name_or_null",
    "reasoning": "Brief explanation of your decision",
    "teaching_approach": "explicit_explanation" | "pattern_highlighting" | "guided_discovery" | "none",
    "examples_needed": true | false,
    "priority": 0.0 to 1.0
}}

If action is "wait", set pattern to "null" and teaching_approach to "none"."""

# ============================================================================
# TEACHING APPROACH PROMPTS
# ============================================================================

TEACHING_APPROACH_SYSTEM_PROMPT = """You are a German language pedagogy expert specializing in grammar instruction. Always respond with valid JSON only, no additional text."""

TEACHING_APPROACH_USER_PROMPT_TEMPLATE = """You are generating a teaching approach for the German grammar pattern: {pattern_name}

Pattern Details:
- Category: {category}
- Difficulty: {difficulty}
- Description: {description}

Learner Profile:
- Learning style: {learning_style}
- Effective teaching methods: {effective_methods}
- Past struggles with this pattern: {struggles}

Teaching approach to use: {teaching_approach}

Available teaching approaches:
- explicit_explanation: Clear rules with examples (great for analytical learners)
- pattern_highlighting: Show patterns visually (great for visual learners)
- guided_discovery: Help learner figure it out themselves (great for immersion learners)

Generate a teaching approach and return ONLY valid JSON in this format:
{{
    "strategy": "{teaching_approach}",
    "explanation": "2-3 sentence explanation appropriate for {learning_style} learners",
    "examples": ["German example with translation", "Another example", "Third example if needed"],
    "practice_suggestion": "Simple exercise or question for learner to practice"
}}

IMPORTANT:
- Examples must be in German with English translations
- Explanation must match the learner's learning style ({learning_style})
- Keep explanation concise (2-3 sentences max)
- Practice suggestion should be actionable and specific"""

# ============================================================================
# LEARNER PROFILING PROMPTS
# ============================================================================

LEARNER_PROFILING_SYSTEM_PROMPT = """You are a language learning pedagogy expert. Always respond with valid JSON only."""

LEARNER_PROFILING_USER_PROMPT_TEMPLATE = """You are analyzing this learner's grammar learning patterns.

Recent Grammar Interactions:
- Errors in last few turns: {recent_errors}
- Mastered patterns: {mastered_patterns}
- Teaching strategy effectiveness: {strategy_effectiveness}
- Current profile: {current_profile} learner

Determine:
1. Learning style (analytical | visual | immersion | unknown)
2. Most effective teaching methods
3. Patterns they struggle with
4. Patterns they excel at
5. Optimal teaching frequency (how often to teach grammar)

Return ONLY valid JSON in this format:
{{
    "learning_style": "analytical" | "visual" | "immersion" | "unknown",
    "effective_methods": ["method1", "method2"],
    "struggle_patterns": ["pattern1", "pattern2"],
    "strength_patterns": ["pattern1", "pattern2"],
    "optimal_frequency": "every_X_turns"
}}

Learning styles:
- analytical: Prefers rules, explanations, explicit grammar instruction
- visual: Prefers examples, patterns, color-coded highlighting
- immersion: Prefers learning through context, conversation, exposure
- unknown: Not enough data to determine

Optimal frequency guidelines:
- every_8_turns: Learner who thrives with frequent, short lessons
- every_10_turns: Balanced approach (default)
- every_12_turns: Learner who prefers more conversation between lessons
- every_15_turns: Learner who needs significant flow time between lessons"""

# ============================================================================
# TOPIC-TO-GRAMMAR MAPPING PROMPTS
# ============================================================================

TOPIC_GRAMMAR_SYSTEM_PROMPT = """You are an expert on German grammar patterns and their relevance to conversation topics. Given a topic, identify which grammar patterns are most commonly used."""

TOPIC_GRAMMAR_USER_PROMPT_TEMPLATE = """Given the conversation topic "{topic}", which German grammar patterns from this list are most relevant?

Available patterns:
{available_patterns}

Return only the pattern names, separated by commas, most relevant first."""

# ============================================================================
# PROMPT CONFIGURATION
# ============================================================================

# LLM parameters for different prompt types
TEACHING_DECISION_PARAMS = {
    "temperature": 0.3,  # Lower temperature for structured decisions
    "max_tokens": 200,
    "response_format": "json"
}

TEACHING_APPROACH_PARAMS = {
    "temperature": 0.5,  # Slightly higher for creative explanations
    "max_tokens": 300,
    "response_format": "json"
}

LEARNER_PROFILING_PARAMS = {
    "temperature": 0.3,  # Lower for consistent analysis
    "max_tokens": 250,
    "response_format": "json"
}

TOPIC_GRAMMAR_PARAMS = {
    "temperature": 0.2,  # Very low for factual mapping
    "max_tokens": 100,
    "response_format": None  # Plain text, not JSON
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def build_teaching_decision_prompt(
    cefr_level: str,
    confidence: str,
    recent_errors: list,
    mastered_patterns: list,
    weaknesses: list,
    topic: str,
    flow_score: float,
    learner_input: str
) -> tuple[str, str]:
    """
    Build the full teaching decision prompt (system and user).

    Returns:
        tuple: (system_prompt, user_prompt)
    """
    user_prompt = TEACHING_DECISION_USER_PROMPT_TEMPLATE.format(
        cefr_level=cefr_level,
        confidence=confidence,
        recent_errors=recent_errors,
        mastered_patterns=mastered_patterns,
        weaknesses=weaknesses,
        topic=topic,
        flow_score=flow_score,
        learner_input=learner_input
    )
    return TEACHING_DECISION_SYSTEM_PROMPT, user_prompt


def get_prompt_version() -> str:
    """Return the current prompt version."""
    return PROMPT_VERSION


def build_teaching_approach_prompt(
    pattern_name: str,
    category: str,
    difficulty: str,
    description: str,
    learning_style: str,
    effective_methods: list,
    struggles: bool,
    teaching_approach: str
) -> tuple[str, str]:
    """
    Build the full teaching approach prompt (system and user).

    Returns:
        tuple: (system_prompt, user_prompt)
    """
    user_prompt = TEACHING_APPROACH_USER_PROMPT_TEMPLATE.format(
        pattern_name=pattern_name,
        category=category,
        difficulty=difficulty,
        description=description,
        learning_style=learning_style,
        effective_methods=', '.join(effective_methods),
        struggles="Yes" if struggles else "No",
        teaching_approach=teaching_approach
    )
    return TEACHING_APPROACH_SYSTEM_PROMPT, user_prompt


def build_learner_profiling_prompt(
    recent_errors: list,
    mastered_patterns: list,
    strategy_effectiveness: list,
    current_profile: str
) -> tuple[str, str]:
    """
    Build the full learner profiling prompt (system and user).

    Returns:
        tuple: (system_prompt, user_prompt)
    """
    user_prompt = LEARNER_PROFILING_USER_PROMPT_TEMPLATE.format(
        recent_errors=recent_errors,
        mastered_patterns=mastered_patterns,
        strategy_effectiveness=strategy_effectiveness if strategy_effectiveness else "No data yet",
        current_profile=current_profile
    )
    return LEARNER_PROFILING_SYSTEM_PROMPT, user_prompt


def build_topic_grammar_prompt(topic: str, available_patterns: str) -> tuple[str, str]:
    """
    Build the full topic-to-grammar mapping prompt (system and user).

    Returns:
        tuple: (system_prompt, user_prompt)
    """
    user_prompt = TOPIC_GRAMMAR_USER_PROMPT_TEMPLATE.format(
        topic=topic,
        available_patterns=available_patterns
    )
    return TOPIC_GRAMMAR_SYSTEM_PROMPT, user_prompt
