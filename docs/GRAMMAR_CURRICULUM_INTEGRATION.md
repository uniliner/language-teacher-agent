# Integration Notes: GrammarCurriculumAgent

This file shows how to integrate the GrammarCurriculumAgent into the ConversationAgent.

## Step 1: Modify ConversationAgent.__init__

Add the GrammarCurriculumAgent as a dependency:

```python
from .grammar_curriculum import GrammarCurriculumAgent

class ConversationAgent(Agent):
    def __init__(
        self,
        config: AgentConfig,
        learner: Learner,
        llm_client: LLMClient,
        pedagogical_engine: Optional[PedagogicalEngine] = None,
        grammar_curriculum_agent: Optional[GrammarCurriculumAgent] = None,
    ):
        super().__init__(config, learner, llm_client)

        # Pedagogical engine for decision making
        self.pedagogical_engine = pedagogical_engine or PedagogicalEngine(learner)

        # Grammar curriculum agent (create if not provided)
        grammar_config = AgentConfig(
            name="grammar_curriculum",
            description="Manages grammar curriculum and tracks pattern progress",
            target_language=config.target_language,
        )
        self.grammar_curriculum_agent = grammar_curriculum_agent or GrammarCurriculumAgent(
            config=grammar_config,
            learner=learner,
            llm_client=llm_client,
        )

        # ... rest of init
```

## Step 2: Modify _analyze_input to pass valid patterns

Pass the valid pattern names from the curriculum to the LLM client:

```python
def _analyze_input(self, learner_input: str) -> Dict[str, Any]:
    """Analyze learner input for errors and vocabulary."""
    if not self.llm_client:
        return {"errors": [], "vocabulary_used": []}

    try:
        # Get valid pattern names from the curriculum agent
        valid_patterns = GrammarCurriculumAgent.get_valid_pattern_names()

        analysis = self.llm_client.analyze_learner_input(
            learner_input=learner_input,
            target_language=self.config.target_language,
            learner_level=self.learner.current_cefr_level,
            valid_grammar_patterns=valid_patterns,  # NEW: pass patterns
        )
        return analysis
    except Exception as e:
        # Fallback if analysis fails
        print(f"Warning: Analysis failed ({e}), continuing without detailed analysis")
        return {"errors": [], "vocabulary_used": [], "intended_meaning": learner_input}
```

## Step 3: Replace _update_learner_from_interaction with curriculum agent call

Replace the direct `record_grammar_attempt` calls with the curriculum agent's `process` method:

```python
def _update_learner_from_interaction(
    self,
    learner_input: str,
    analysis: Dict[str, Any],
    decision: TeachingDecision,
) -> Dict[str, Any]:
    """Update learner state based on the interaction."""
    updates = {}

    # Track vocabulary used
    for word in analysis.get("vocabulary_used", []):
        vocab_item = self.learner.get_vocabulary(word)
        if vocab_item:
            vocab_item.record_encounter(context=learner_input[:50])
        else:
            # We'd ideally get translations from the analysis
            # For now, skip if we don't have translation info
            pass

    # === MODIFIED: Use GrammarCurriculumAgent for grammar tracking ===
    # OLD CODE (remove this):
    # for error in analysis.get("errors", []):
    #     if error.get("type") == "grammar":
    #         error_pattern = error.get("pattern", "general")
    #         success = error.get("severity") != "major"
    #         self.learner.record_grammar_attempt(error_pattern, success)

    # NEW CODE (add this):
    grammar_result = self.grammar_curriculum_agent.process(
        input_data={
            "errors": analysis.get("errors", []),
            "learner_input": learner_input,
        }
    )

    # Optionally track grammar updates in response
    if grammar_result.get("patterns_updated"):
        updates["grammar_patterns_updated"] = grammar_result["patterns_updated"]
        updates["ready_to_advance"] = grammar_result.get("ready_to_advance", False)
        updates["suggested_focus"] = grammar_result.get("suggested_focus")

    # Update confidence based on session
    error_count = len(analysis.get("errors", []))
    total_turns = self.pedagogical_engine.turn_count
    recent_success = error_count < total_turns * 0.3

    old_confidence = self.learner.confidence
    self.learner.update_confidence(error_count, total_turns, recent_success)

    if old_confidence != self.learner.confidence:
        updates["confidence"] = self.learner.confidence

    # Update stats
    self.learner.stats.total_turns += 1
    self.turns_in_session += 1

    return updates
```

## Summary of Changes

1. **Import** `GrammarCurriculumAgent` in ConversationAgent
2. **Add** `grammar_curriculum_agent` parameter to `__init__` and create instance
3. **Modify** `_analyze_input` to call `GrammarCurriculumAgent.get_valid_pattern_names()` and pass to `analyze_learner_input`
4. **Replace** direct `record_grammar_attempt` calls with `grammar_curriculum_agent.process()`

## Benefits of This Integration

- Grammar errors are now routed to the correct `GrammarPattern` with proper metadata (difficulty, CEFR level, category)
- The curriculum ensures learners progress through patterns in a pedagogically sound order
- The system can suggest the next pattern to focus on
- Mastery tracking ensures learners don't advance too quickly
