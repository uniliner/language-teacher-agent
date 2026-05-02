# Visual Diagram: `_topic_grammar_cache` Usage

## Current State (Phase 2) - Cache Created but Dormant

```
┌─────────────────────────────────────────────────────────────┐
│              GrammarCurriculumAgent                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  _topic_grammar_cache = {                                    │
│    "food": ["accusative_case", "indefinite_articles"],       │
│    "directions": ["prepositions_accusative", ...],           │
│    ...                                                        │
│  }                                                           │
│                                                              │
│  ❌ NOT USED YET - Waiting for Phase 3 & 4                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Future State (Phase 3 & 4) - Active Usage

```
CONVERSATION START
        │
        ▼
┌─────────────────────────────────────────┐
│  Learner says: "I want to talk about   │
│  ordering food in a restaurant"         │
└─────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────┐
│  Agent detects topic: "food"            │
└─────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────┐
│  _get_grammar_for_topic("food")         │
│                                         │
│  1. Check cache: _topic_grammar_cache   │
│     └──> Found! ["accusative_case",     │
│                "indefinite_articles"]   │
│                                         │
│  2. Check learner's mastered patterns   │
│     └──> accusative_case NOT mastered   │
│         indefinite_articles NOT mastered│
└─────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────┐
│  AGENTIC DECISION: Proactively teach    │
│  accusative_case BEFORE errors occur    │
└─────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────┐
│  Agent response: "Great! Let's talk    │
│  about food. First, let me quickly      │
│  explain accusative case - you'll need  │
│  it to say 'I want an apple' (einen     │
│  Apfel) instead of 'ein Apfel'."        │
└─────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────┐
│  Learner uses accusative case correctly │
│  (or makes errors that agent corrects)   │
└─────────────────────────────────────────┘
        │
        ▼
    LEARNING HAPPENS
```

## Performance Comparison

### WITHOUT CACHE (Hypothetical LLM-Only Approach)

```
Turn 1: Topic = "food"
├─> LLM Call: "What grammar for food?" (500ms, $0.0015)
├─> Result: ["accusative_case", "indefinite_articles"]
└─> Teach accusative_case

Turn 2: Topic = "food"
├─> LLM Call: "What grammar for food?" (500ms, $0.0015)
├─> Result: ["accusative_case", "indefinite_articles"]
└─> Teach indefinite_articles

Turn 3: Topic = "food"
├─> LLM Call: "What grammar for food?" (500ms, $0.0015)
├─> Result: ["accusative_case", "indefinite_articles"]
└─> Review patterns

Total: 3 LLM calls, 1500ms, $0.0045
```

### WITH CACHE (Implemented Approach)

```
Turn 1: Topic = "food"
├─> Cache Lookup: _topic_grammar_cache["food"] (<1ms, $0)
├─> Result: ["accusative_case", "indefinite_articles"]
└─> Teach accusative_case

Turn 2: Topic = "food"
├─> Cache Lookup: _topic_grammar_cache["food"] (<1ms, $0)
├─> Result: ["accusative_case", "indefinite_articles"]
└─> Teach indefinite_articles

Turn 3: Topic = "food"
├─> Cache Lookup: _topic_grammar_cache["food"] (<1ms, $0)
├─> Result: ["accusative_case", "indefinite_articles"]
└─> Review patterns

Total: 0 LLM calls, <3ms, $0
```

## Real-World Example Flow

### Scenario: Learner wants to discuss "daily routine"

```python
# ========== STEP 1: Detect Topic ==========
topic = detect_conversation_topic(learner_input)
# Result: "daily routine"

# ========== STEP 2: Look Up Relevant Grammar ==========
relevant_patterns = GrammarCurriculumAgent._topic_grammar_cache[topic]
# Result: ["separable_verbs_basic", "present_tense_regular"]

# ========== STEP 3: Check Learner State ==========
learner_patterns = learner.grammar_patterns.keys()
# Result: ["present_tense_regular"]  (already knows present tense)

# ========== STEP 4: Make Agentic Decision ==========
missing_patterns = [p for p in relevant_patterns if p not in learner_patterns]
# Result: ["separable_verbs_basic"]  (doesn't know separable verbs)

if missing_patterns:
    return {
        "action": "introduce_pattern",
        "pattern": "separable_verbs_basic",
        "reason": f"Topic '{topic}' requires separable verbs (e.g., aufstehen, mitkommen)",
        "timing": "before_topic_practice"
    }

# ========== STEP 5: Execute Teaching ==========
Agent: "Perfect! Let's talk about your daily routine. Before we start, 
        let me quickly explain separable prefix verbs - you'll use them 
        a lot when describing your morning routine. For example, 
        'aufstehen' (to get up) splits in two: 'Ich stehe um 8 Uhr auf.'"

# ========== STEP 6: Practice ==========
Learner: "Ich stehe um 8 Uhr auf und dann dusche ich."
Agent: "Great! You're using separable verbs correctly."
```

## Cache Evolution Over Time

### Initial State (Code Deployment)
```python
_topic_grammar_cache = {
    "daily routine": ["separable_verbs_basic", "present_tense_regular"],
    "past events": ["perfect_tense_haben", "perfect_tense_sein"],
    "describing things": ["adjective_endings_basic", "noun_gender"],
    "family": ["definite_articles_nominative", "possessive_articles"],
    "food": ["accusative_case", "indefinite_articles_nominative"],
    "directions": ["prepositions_accusative", "two_way_prepositions"],
    "future plans": ["future_tense", "modal_verbs_present"],
}
# 7 pre-defined topics
```

### After 1 Month of Usage (LLM-Generated Entries Added)
```python
_topic_grammar_cache = {
    # ... original 7 topics ...
    
    # LLM-generated entries from real conversations
    "weather": ["present_tense_regular", "accusative_case"],
    "hobbies": ["modal_verbs_present", "accusative_case"],
    "job interview": ["formal_you", "future_tense", "perfect_tense"],
    "travel": ["prepositions_accusative", "modal_verbs_present"],
    "cooking": ["imperative", "accusative_case"],
    "technology": ["passive_present", "accusative_case"],
}
# 13 topics (7 static + 6 LLM-generated)
```

### After 6 Months of Usage
```python
_topic_grammar_cache = {
    # ... 50+ topics ...
}
# Rich coverage of conversation topics
# Minimal LLM calls (only for brand-new topics)
```

## Key Insight: The Cache is "Agentic Infrastructure"

**Reactive Agent** (Current - Phase 1 & 2):
```
Error occurs → Agent reacts → Teaches pattern
```

**Proactive Agent** (Future - Phase 3 & 4 with cache):
```
Topic detected → Cache lookup → Teaches pattern BEFORE errors
```

The cache enables the transformation from **reactive** to **proactive** teaching.
