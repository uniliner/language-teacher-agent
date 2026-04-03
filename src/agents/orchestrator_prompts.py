"""
Orchestration prompts for the agentic conversation system.

This module contains prompts that guide the LLM to reason about what
the learner needs and decide which specialist agents to call.

This is the heart of the ReAct pattern: Reason → Act → Observe.
"""

from typing import Any, Dict, List


# ============================================================================
# ORCHESTRATION SYSTEM PROMPT
# ============================================================================

ORCHESTRATOR_SYSTEM_PROMPT = """You are an expert language teaching orchestrator for a German learning app.

Your job is to analyze a learner's situation and decide what teaching actions to take.

You have access to specialist agents:
1. **grammar_curriculum**: Tracks grammar patterns in a structured curriculum (A1→B1). Call this to record grammar errors and track mastery progress.

2. **pronunciation_teaching**: Teaches pronunciation patterns. Call this when the learner needs help with sounds, accent, or pronunciation rules.

## Your Decision Process

For each learner input, you should:

1. **Analyze the learner's state**:
   - What errors did they make? (severity, type, recurring?)
   - What is their confidence level? (VERY_LOW to VERY_HIGH)
   - What is their CEFR level? (A1, A2, B1, etc.)
   - How is the conversation flowing? (struggling vs. natural)

2. **Reason about what they need NOW**:
   - Are they struggling? Prioritize getting back on track over teaching new concepts.
   - Is their confidence low? Be encouraging and gentle.
   - Are they making the same error repeatedly? This needs attention.
   - Have we not introduced new material in a while? Maybe time for something new.
   - Are there pronunciation patterns due for review?

3. **Decide which specialists to call**:
   - You can call ZERO, ONE, or MULTIPLE specialists per turn.
   - Each specialist should have a clear purpose.
   - Don't call specialists if there's no clear need.

## Specialist Capabilities

**grammar_curriculum**:
- Call when: learner made grammar errors, or you want to check curriculum progress
- Purpose: "track_error", "check_progress", "get_next_pattern"
- Tracks: Which grammar patterns the learner has encountered, their mastery scores

**pronunciation_teaching**:
- Call when: learner has pronunciation issues, or it's been a while since pronunciation practice
- Purpose: "teach_new_pattern", "review_due_pattern", "address_context_pronunciation"
- Teaches: Sound patterns, accent reduction, common pronunciation mistakes

## Teaching Strategies

Choose the appropriate strategy for the situation:

- **Gentle correction**: For low-confidence learners or minor errors
- **Explicit explanation**: For major errors or new concepts
- **Pattern highlighting**: For recurring issues
- **Spaced repetition**: For reviewing material that's due for practice
- **Challenge providing**: For high-confidence learners who need to grow
- **Confidence building**: For learners who are struggling
- **Flow preservation**: When conversation is going well, don't interrupt

## Important Principles

1. **One thing at a time**: Don't overwhelm the learner. If they made 5 errors, address the most important one, not all 5.

2. **Flow matters more than perfection**: If the learner is struggling to express themselves, prioritize communication over correctness.

3. **Confidence is fragile**: Very low confidence learners need encouragement, not constant correction.

4. **Recycle intelligently**: Review material that the learner is weak on, not just "random old material."

5. **Adapt to the individual**: A learner who makes few errors needs different teaching than one who struggles constantly.

Your output must be structured JSON that will be parsed by the system. Be precise and follow the schema exactly."""


# ============================================================================
# ORCHESTRATION USER PROMPT TEMPLATE
# ============================================================================

def build_orchestration_prompt(
    learner_input: str,
    detected_errors: List[Dict[str, Any]],
    learner_state: Dict[str, Any],
    conversation_context: Dict[str, Any],
) -> str:
    """
    Build the orchestration prompt for a specific turn.

    Args:
        learner_input: What the learner said
        detected_errors: Errors detected by LLM analysis
        learner_state: Current learner state (confidence, level, etc.)
        conversation_context: Conversation history and context

    Returns:
        Prompt string for the LLM
    """

    # Format errors for readability
    errors_str = _format_errors(detected_errors)

    # Format learner state
    state_str = _format_learner_state(learner_state)

    # Format conversation context
    context_str = _format_conversation_context(conversation_context)

    prompt = f"""Analyze this learning situation and decide what to do.

## Learner Input
"{learner_input}"

## Detected Errors
{errors_str}

## Learner State
{state_str}

## Conversation Context
{context_str}

## Your Task

Think through this step by step:

1. **What's happening here?** (Learner's meaning, errors, confidence level)

2. **What does this learner need RIGHT NOW?** (Not "what's the textbook next step" but "what will help THIS learner at THIS moment")

3. **Which specialists should I call and why?**

4. **What teaching strategy fits this situation?**

Then, output your decision as JSON in this exact format:

```json
{{
  "thoughts": "Brief explanation of your reasoning (2-3 sentences)",
  "actions": [
    {{
      "specialist": "grammar_curriculum",
      "purpose": "track_error",
      "priority": 1
    }}
  ],
  "teaching_strategy": "gentle_correction",
  "confidence": 0.9,
  "response_guidance": "Brief notes for the response generator (e.g., 'Correct accusative error gently, then ask follow-up question about topic')"
}}
```

### Action Schema

- **specialist** (string): Must be one of: ["grammar_curriculum", "pronunciation_teaching"]
- **purpose** (string): Why you're calling this specialist (depends on specialist)
  - For grammar_curriculum: "track_error", "check_progress", "get_next_pattern"
  - For pronunciation_teaching: "teach_new_pattern", "review_due_pattern", "address_context_pronunciation"
- **priority** (int): 1=highest, 2=medium, 3=lowest (defines execution order)

### Teaching Strategy Options

Choose one: ["gentle_correction", "explicit_explanation", "pattern_highlighting", "spaced_repetition", "challenge_providing", "confidence_building", "flow_preservation"]

### Important Notes

- **actions can be empty array** [] if no specialists are needed this turn
- **You can call multiple specialists** if the learner needs multiple types of help
- **confidence** is how sure you are about this decision (0.0 to 1.0)
- **response_guidance** helps the final response generator understand your intent

Now, analyze and respond with JSON only:"""

    return prompt


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _format_errors(errors: List[Dict[str, Any]]) -> str:
    """Format detected errors for the prompt."""
    if not errors:
        return "No errors detected."

    formatted = []
    for i, error in enumerate(errors, 1):
        severity = error.get("severity", "unknown")
        error_type = error.get("type", "unknown")
        pattern = error.get("pattern", error.get("category", ""))
        message = error.get("message", "")
        recurring = error.get("recurring", False)

        entry = f"{i}. **{severity.upper()}** {error_type}"
        if pattern:
            entry += f" (pattern: {pattern})"
        if message:
            entry += f"\n   {message}"
        if recurring:
            entry += " ⚠️ RECURRING ERROR"

        formatted.append(entry)

    return "\n".join(formatted)


def _format_learner_state(state: Dict[str, Any]) -> str:
    """Format learner state for the prompt."""
    lines = [
        f"- **Confidence Level**: {state.get('confidence', 'UNKNOWN')}",
        f"- **CEFR Level**: {state.get('cefr_level', 'UNKNOWN')}",
        f"- **Total Turns**: {state.get('total_turns', 0)}",
    ]

    # Vocabulary stats
    vocab_size = state.get('vocabulary_size', 0)
    if vocab_size:
        lines.append(f"- **Vocabulary**: {vocab_size} words encountered")

    # Grammar patterns
    grammar_patterns = state.get('grammar_patterns', {})
    if grammar_patterns:
        mastered = sum(1 for p in grammar_patterns.values() if p.get('mastery_score', 0) >= 0.7)
        lines.append(f"- **Grammar**: {mastered}/{len(grammar_patterns)} patterns mastered (≥70%)")

    # Recent error rate
    if 'recent_error_rate' in state:
        lines.append(f"- **Recent Error Rate**: {state['recent_error_rate']:.1%}")

    return "\n".join(lines)


def _format_conversation_context(context: Dict[str, Any]) -> str:
    """Format conversation context for the prompt."""
    lines = []

    if 'topic' in context:
        lines.append(f"- **Topic**: {context['topic']}")

    if 'turn_number' in context:
        lines.append(f"- **Turn Number**: {context['turn_number']}")

    if 'flow_score' in context:
        flow = context['flow_score']
        flow_desc = "flowing well" if flow > 0.6 else "somewhat struggling" if flow > 0.3 else "struggling"
        lines.append(f"- **Conversation Flow**: {flow:.2f}/1.0 ({flow_desc})")

    if 'recent_conversation_summary' in context:
        lines.append(f"- **Recent Context**: {context['recent_conversation_summary']}")

    if not lines:
        return "No additional context."

    return "\n".join(lines)


# ============================================================================
# VALIDATION SCHEMAS
# ============================================================================

VALID_SPECIALISTS = ["grammar_curriculum", "pronunciation_teaching"]

VALID_PURPOSES = {
    "grammar_curriculum": ["track_error", "check_progress", "get_next_pattern"],
    "pronunciation_teaching": ["teach_new_pattern", "review_due_pattern", "address_context_pronunciation"],
}

VALID_STRATEGIES = [
    "gentle_correction",
    "explicit_explanation",
    "pattern_highlighting",
    "spaced_repetition",
    "challenge_providing",
    "confidence_building",
    "flow_preservation",
]


def validate_orchestration_decision(decision: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Validate an orchestration decision from the LLM.

    Args:
        decision: The parsed JSON decision from the LLM

    Returns:
        (is_valid, list_of_errors)
    """
    errors = []

    # Check required fields
    required_fields = ["thoughts", "actions", "teaching_strategy", "confidence"]
    for field in required_fields:
        if field not in decision:
            errors.append(f"Missing required field: {field}")

    # Validate actions
    actions = decision.get("actions", [])
    if not isinstance(actions, list):
        errors.append("'actions' must be a list")
    else:
        for i, action in enumerate(actions):
            if not isinstance(action, dict):
                errors.append(f"Action {i} is not a dict")
                continue

            specialist = action.get("specialist")
            if specialist not in VALID_SPECIALISTS:
                errors.append(f"Action {i}: Invalid specialist '{specialist}'. Must be one of {VALID_SPECIALISTS}")

            purpose = action.get("purpose")
            if specialist in VALID_PURPOSES and purpose not in VALID_PURPOSES[specialist]:
                errors.append(f"Action {i}: Invalid purpose '{purpose}' for {specialist}. Must be one of {VALID_PURPOSES[specialist]}")

    # Validate teaching_strategy
    strategy = decision.get("teaching_strategy")
    if strategy not in VALID_STRATEGIES:
        errors.append(f"Invalid teaching_strategy '{strategy}'. Must be one of {VALID_STRATEGIES}")

    # Validate confidence
    confidence = decision.get("confidence")
    if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
        errors.append(f"'confidence' must be a number between 0.0 and 1.0, got {confidence}")

    return len(errors) == 0, errors
