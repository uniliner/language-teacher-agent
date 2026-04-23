# GrammarCurriculumAgent Agentic Upgrade Plan

## Executive Summary

**Current State**: GrammarCurriculumAgent is a reactive, static curriculum tracker that processes errors when they occur but lacks autonomous decision-making and learning capabilities.

**Target State**: Fully agentic GrammarCurriculumAgent that autonomously decides what grammar to teach, when to teach it, learns from learner interactions, and adapts its teaching approach to individual learners.

**Time Estimate**: 12-15 hours of implementation

**Learning Focus**: Building autonomous agents with learning capabilities, LLM-driven decision making, and adaptive curriculum management

---

## 🎯 Current Architecture Analysis

### What GrammarCurriculumAgent Currently Does

```python
# src/agents/grammar_curriculum.py (current)

class GrammarCurriculumAgent(Agent):
    # Static curriculum (hardcoded)
    GERMAN_GRAMMAR_CURRICULUM = [
        CurriculumPattern(...),  # 28 fixed patterns
    ]

    def process(self, input_data: Dict) -> Dict:
        """
        Reactive: Processes errors when they come in
        """
        for error in errors:
            # Route error to pattern
            pattern.record_attempt(success)

        # Simple advancement check
        ready = self.is_ready_to_advance()  # mastery >= 0.7
        next_pattern = self.get_next_pattern()  # sequential

        return {
            "patterns_updated": [...],
            "ready_to_advance": ready,
            "suggested_focus": next_pattern,
        }
```

### Limitations

1. **No Autonomy**: Can't decide to teach grammar on its own - only reacts to errors
2. **No Learning**: Doesn't learn which teaching approaches work best for this learner
3. **Static Curriculum**: Fixed sequence doesn't adapt to learner needs
4. **No Strategic Thinking**: Doesn't consider conversation flow, confidence, context
5. **No LLM Integration**: All logic is rule-based, no AI reasoning
6. **No Proactive Teaching**: Can't introduce patterns before errors occur
7. **No Self-Reflection**: Doesn't track or improve its own teaching effectiveness

---

## 🚀 Target Architecture: Fully Agentic GrammarCurriculumAgent

### Core Principles

```
┌─────────────────────────────────────────────────────────────┐
│              AGENTIC GRAMMAR CURRICULUM AGENT               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. PERCEIVE   ← Gather context (learner state, flow, etc)  │
│  2. REASON     ← LLM decides what to do                      │
│  3. ACT        ← Teach, review, assess, or wait             │
│  4. REFLECT    ← Learn from effectiveness                    │
│  5. ADAPT      ← Update strategies based on what works      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Key Capabilities

#### 1. Autonomous Decision Making
```python
def decide_action(self, context: Dict) -> GrammarTeachingDecision:
    """
    LLM-driven decision making about what to do.

    Returns one of:
    - INTRODUCE_PATTERN: Teach new grammar pattern
    - REVIEW_PATTERN: Practice due pattern
    - REINFORCE_PATTERN: Strengthen weak pattern
    - ASSESS_READINESS: Check if learner is ready for next level
    - WAIT: Don't interrupt conversation flow
    - DIAGNOSE_ISSUE: Investigate persistent errors
    """
```

#### 2. Learning from Interactions
```python
class TeachingStrategyTracker:
    """
    Track which teaching approaches work for THIS learner.

    Example:
    - Explicit explanations: 70% success rate
    - Pattern highlighting: 85% success rate
    - Gentle recast: 60% success rate
    """
    strategy_effectiveness: Dict[str, StrategyStats]

class LearnerGrammarProfile:
    """
    Learn about this learner's grammar learning style.

    Example:
    - Visual learner: responds well to examples
    - Analytical: responds well to rules
    - Immersion: learns through context
    """
    learning_style: str
    preferred_teaching_methods: List[str]
    error_prone_patterns: List[str]
    strength_patterns: List[str]
```

#### 3. Dynamic Curriculum Management
```python
class AdaptiveCurriculum:
    """
    Reorder curriculum based on learner needs.

    Example:
    Learner struggles with word order → move separable_verbs_basic earlier
    Learner excels at articles → move advanced patterns earlier
    """
    def reorder_patterns(self, learner_weaknesses, learner_strengths)
    def prerequisite_check(self, pattern, learner_state)
    def personalize_sequence(self, learner_profile)
```

#### 4. Context-Aware Teaching
```python
def should_teach_grammar(self, context: Dict) -> bool:
    """
    Strategic decision: Is NOW the right time?

    Considers:
    - Conversation flow (don't interrupt if < 0.4)
    - Learner confidence (don't overwhelm if VERY_LOW)
    - Recent error patterns (are there recurring errors?)
    - Pattern dependencies (is learner ready for this pattern?)
    - Teaching frequency (not too often - every ~10 turns)
    - Topic relevance (does this grammar fit the topic?)
    """
```

---

## 📋 Implementation Plan

### Phase 1: Foundation (2 hours)
**Goal**: Add LLM integration and basic decision-making

#### 1.1 Add LLM Integration
```python
# src/agents/grammar_curriculum.py

class GrammarCurriculumAgent(Agent):
    def __init__(self, config, learner, llm_client):
        super().__init__(config, learner, llm_client)
        # NOW we actually use llm_client!

    def _generate_teaching_plan(self, context: Dict) -> Dict:
        """
        Use LLM to decide what grammar to teach and how.

        Prompt includes:
        - Learner's current grammar state
        - Recent errors and patterns
        - Conversation context (flow, topic)
        - Available patterns to teach
        - Teaching strategy options

        Returns:
        {
            "action": "introduce_pattern" | "review_pattern" | "wait",
            "pattern": "accusative_case",
            "reasoning": "Learner keeps making accusative errors...",
            "teaching_approach": "explicit_explanation",
            "examples_needed": True,
            "priority": 0.8,
        }

        FALLBACK STRATEGY: If LLM fails, use rule-based decision
        """
        try:
            # LLM-based decision (see below for implementation)
            return self._llm_teaching_decision(context)
        except Exception as e:
            print(f"[GrammarCurriculum] LLM decision failed ({e}), using fallback")
            return self._rule_based_teaching_decision(context)

    def _llm_teaching_decision(self, context: Dict) -> Dict:
        """
        LLM-driven teaching decision with proper JSON schema.

        Returns structured JSON dict with action, pattern, reasoning, etc.
        """
        prompt = f"""You are a pedagogical grammar expert. Decide what grammar teaching action to take.

Learner State:
- Level: {context['learner_state']['cefr_level']}
- Confidence: {context['learner_state']['confidence']}
- Recent errors: {context['learner_state']['recent_errors']}
- Mastered patterns: {list(context['learner_state']['mastered_patterns'].keys())}
- Current weaknesses: {context['learner_state']['weaknesses']}

Conversation Context:
- Topic: {context['conversation']['topic']}
- Flow score: {context['conversation']['flow_score']} (0.0 = struggling, 1.0 = flowing)
- Recent learner input: {context['conversation']['recent_input']}

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

        response = self.llm_client.generate_response(
            system_prompt="You are a German grammar pedagogy expert. Always respond with valid JSON only, no additional text.",
            user_message=prompt,
            temperature=0.3,  # Lower temperature for more structured output
            max_tokens=200,
            response_format="json"  # Request JSON format from LLM
        )

        # Parse JSON response
        teaching_plan = json.loads(response)

        # Validate required fields
        required_fields = ["action", "pattern", "reasoning", "teaching_approach", "priority"]
        for field in required_fields:
            if field not in teaching_plan:
                raise ValueError(f"Missing required field: {field}")

        # Convert "null" string to None
        if teaching_plan.get("pattern") == "null":
            teaching_plan["pattern"] = None

        return teaching_plan

    def _rule_based_teaching_decision(self, context: Dict) -> Dict:
        """
        Fallback: Rule-based decision when LLM fails.

        STRATEGY: Use highest-priority teaching trigger directly
        """
        triggers = self._get_teaching_triggers(context)

        if not triggers:
            return {
                "action": "wait",
                "pattern": None,
                "reasoning": "No teaching triggers available (LLM fallback)",
                "teaching_approach": "none",
                "examples_needed": False,
                "priority": 0.0,
            }

        # Use highest-priority trigger
        top_trigger = triggers[0]

        return {
            "action": self._map_trigger_type_to_action(top_trigger["type"]),
            "pattern": top_trigger["pattern"],
            "reasoning": f"Rule-based fallback: {top_trigger['type']}",
            "teaching_approach": "explicit_explanation",  # Default for fallback
            "examples_needed": True,
            "priority": top_trigger["priority"],
        }

    def _map_trigger_type_to_action(self, trigger_type: str) -> str:
        """Map trigger type to action string."""
        mapping = {
            "review_due": "review_pattern",
            "recurring_error": "reinforce_pattern",
            "prerequisite_ready": "introduce_pattern",
        }
        return mapping.get(trigger_type, "wait")
```

#### 1.2 Implement Agentic `process()` Method
```python
def process(self, input_data: Dict) -> Dict:
    """
    AGENTIC VERSION: ReAct loop for grammar teaching

    1. PERCEIVE: Gather context
    2. REASON: LLM decides what to do
    3. ACT: Teach/Review/Assess/Wait
    4. REFLECT: Track effectiveness
    5. UPDATE: Modify learner state
    """
    # Load persisted teaching state on first call
    if not self.teaching_strategy_tracker and not self.learner_profile:
        self._load_teaching_state()

    # Step 1: Gather context
    context = self._build_teaching_context(input_data)

    # Step 2: LLM reasoning (with fallback)
    teaching_plan = self._generate_teaching_plan(context)

    # Step 3: Execute decision
    result = self._execute_teaching_plan(teaching_plan, context)

    # Step 4: Reflect and learn
    self._track_teaching_effectiveness(
        teaching_action=teaching_plan,  # The action we took
        result=result,                   # The result of executing it
        current_turn_errors=context.get("errors", []),  # Errors in this turn
        context=context                  # Full context for learning style detection
    )

    # Step 5: Save teaching state for persistence
    self._save_teaching_state()

    return result
```

---

### Phase 2: Learning & Adaptation (3 hours)
**Goal**: Learn from learner interactions and adapt teaching

#### 2.1 Teaching Strategy Tracker & State Persistence
```python
# src/models/grammar_teaching.py (new file)

@dataclass
class StrategyStats:
    """Track effectiveness of a teaching strategy."""
    strategy_name: str
    attempts: int = 0
    successful_corrections: int = 0  # learner used correctly next time
    learner_engagement: float = 0.0  # did learner try to use it?
    avg_mastery_improvement: float = 0.0

    @property
    def success_rate(self) -> float:
        return self.successful_corrections / max(self.attempts, 1)

class GrammarCurriculumAgent(Agent):
    # Class-level cache for topic-to-grammar mapping (shared across instances)
    _topic_grammar_cache: ClassVar[Dict[str, List[str]]] = {
        "daily routine": ["separable_verbs_basic", "present_tense_regular"],
        "past events": ["perfect_tense_haben", "perfect_tense_sein"],
        "describing things": ["adjective_endings_basic", "noun_gender"],
        "family": ["definite_articles_nominative", "possessive_articles"],
        "food": ["accusative_case", "indefinite_articles_nominative"],
        "directions": ["prepositions_accusative", "two_way_prepositions"],
        "future plans": ["future_tense", "modal_verbs_present"],
    }

    def __init__(self, ...):
        # Track what works for THIS learner
        self.teaching_strategy_tracker: Dict[str, StrategyStats] = {}
        self.learner_profile = LearnerGrammarProfile()

        # Track pending teaching actions to evaluate effectiveness on next turn
        self._pending_teaching_action: Optional[Dict] = None

        # Learning style detection: cache and throttle
        self._learning_style_detection_turns: int = 0
        self._learning_style_detection_interval: int = 50  # Detect every 50 turns

    def _load_teaching_state(self):
        """
        Load teaching state from learner's persisted data.

        PERSISTENCE STRATEGY: Piggyback on existing Learner model

        The Learner model already has persistence via MemoryStore.
        We add grammar teaching state as a dict field on Learner:
        - learner.grammar_teaching_state = {
        -     "strategy_tracker": {...},
        -     "learner_profile": {...},
        -     "pending_action": {...}
        - }

        This way, when MemoryStore.save_learner() is called,
        all teaching insights are saved automatically.
        """
        if hasattr(self.learner, 'grammar_teaching_state') and self.learner.grammar_teaching_state:
            state = self.learner.grammar_teaching_state

            # Restore strategy tracker
            if "strategy_tracker" in state:
                for strategy_name, stats_data in state["strategy_tracker"].items():
                    self.teaching_strategy_tracker[strategy_name] = StrategyStats(**stats_data)

            # Restore learner profile
            if "learner_profile" in state:
                self.learner_profile = LearnerGrammarProfile(**state["learner_profile"])

            # Restore pending action
            if "pending_action" in state:
                self._pending_teaching_action = state["pending_action"]

    def _save_teaching_state(self):
        """
        Save teaching state to learner model for persistence.

        Called at end of process() after any updates.
        """
        # Convert strategy tracker to serializable dict
        strategy_tracker_dict = {
            name: asdict(stats) if hasattr(stats, '__dict__') or hasattr(stats, '__dataclass_fields__')
            else stats.__dict__
            for name, stats in self.teaching_strategy_tracker.items()
        }

        self.learner.grammar_teaching_state = {
            "strategy_tracker": strategy_tracker_dict,
            "learner_profile": self.learner_profile.model_dump(),
            "pending_action": self._pending_teaching_action,
        }

        # MemoryStore.save_learner() will be called by ConversationAgent
```

#### 2.2 Learner Profiling
```python
class LearnerGrammarProfile(BaseModel):
    """
    Learn about this learner's grammar learning characteristics.
    """
    # Learning style (detected from interactions)
    learning_style: Literal["analytical", "visual", "immersion", "unknown"]
    preferred_explanation_length: Literal["brief", "detailed", "adaptive"]

    # What works for this learner
    effective_teaching_methods: List[str] = []
    ineffective_teaching_methods: List[str] = []

    # Grammar patterns
    error_prone_patterns: List[str] = []  # patterns with high error rate
    strength_patterns: List[str] = []  # patterns mastered quickly
    problematic_pattern_combinations: List[Tuple[str, str]] = []

    # Learning patterns
    avg_attempts_to_mastery: float = 0.0
    retention_rate: float = 0.0  # how well they remember
    practice_frequency_preference: str = "adaptive"

    def update_learning_style(self, detected_style: str):
        """
        Update learning style from detection.

        This is called by the agent's _detect_learning_style() method.
        The agent owns the LLM client; the model just stores the result.
        """
        if detected_style in ["analytical", "visual", "immersion"]:
            self.learning_style = detected_style
```

#### 2.3 Effectiveness Tracking
```python
def _track_teaching_effectiveness(
    self,
    teaching_action: Dict,
    result: Dict,
    current_turn_errors: List[Dict]
):
    """
    Did our teaching work?

    DESIGN: We evaluate effectiveness in TWO places:
    1. HERE (called at END of turn): Check if previous teaching helped in THIS turn
    2. NEXT TURN: Check if current teaching helps in the FOLLOWING turn

    This bridges the timing gap by:
    - Storing pending teaching action when we teach
    - Evaluating it when we see the next learner input
    - Checking both immediate and next-turn effectiveness

    Check:
    1. Did previous teaching help in THIS turn? (evaluate pending action)
    2. Store CURRENT teaching to evaluate on NEXT turn
    """
    # Step 1: Evaluate PREVIOUS teaching action (from last turn)
    if self._pending_teaching_action is not None:
        previous_pattern = self._pending_teaching_action["pattern"]
        previous_strategy = self._pending_teaching_action["teaching_approach"]

        # Check if learner used previous pattern correctly in THIS turn
        success = self._check_pattern_usage_in_current_turn(
            previous_pattern, current_turn_errors
        )

        # Update strategy tracker with results
        if previous_strategy not in self.teaching_strategy_tracker:
            self.teaching_strategy_tracker[previous_strategy] = StrategyStats(previous_strategy)

        self.teaching_strategy_tracker[previous_strategy].attempts += 1
        if success:
            self.teaching_strategy_tracker[previous_strategy].successful_corrections += 1

        # Update learner profile
        pattern_data = self.learner.grammar_patterns.get(previous_pattern)
        pattern_mastery_data = {
            "attempts": pattern_data.attempts if pattern_data else 0,
            "mastery_score": pattern_data.mastery_score if pattern_data else 0.0,
        }
        self.learner_profile.update_from_teaching_result(
            previous_pattern, previous_strategy, success, pattern_mastery_data
        )

        # Periodically run learning style detection (throttled)
        self._detect_learning_style(context)

    # Step 2: Store CURRENT teaching action for NEXT turn evaluation
    if result.get("action") in ["introduce_pattern", "review_pattern", "reinforce_pattern"]:
        self._pending_teaching_action = {
            "pattern": teaching_action["pattern"],
            "teaching_approach": teaching_action["teaching_approach"],
            "timestamp": datetime.now(),
        }
    else:
        self._pending_teaching_action = None

def _check_pattern_usage_in_current_turn(
    self,
    pattern_name: str,
    current_errors: List[Dict]
) -> bool:
    """
    Check if learner used the pattern correctly in the current turn.

    ⚠️ **LIMITATION**: This implementation checks only for absence of errors.
    It does NOT confirm the learner actually attempted to use the pattern.
    They may have simply not encountered a context requiring it.

    Current implementation returns True if:
    - No errors in this pattern's category

    This may OVERESTIMATE teaching effectiveness.

    **STRICTER IMPLEMENTATION** (recommended before production):
    ```python
    # Option 1: Check learner input for grammar category tokens
    learner_input = context.get("learner_input", "")
    pattern_tokens = self._get_pattern_tokens(pattern_name)  # e.g., "den", "die", "das" for accusative
    return any(token in learner_input for token in pattern_tokens) and no_errors

    # Option 2: Track explicit practice attempts
    return context.get("practiced_pattern") == pattern_name and no_errors

    # Option 3: Use multi-turn window with decay
    # Check last 3 turns for pattern usage, weight recent more heavily
    ```
    """
    pattern_category = self._get_pattern_category(pattern_name)

    # Check if any errors in this pattern's category
    for error in current_errors:
        if error.get("category") == pattern_category:
            return False  # Error in this category = not successful

    # ⚠️ Simplified check: absence of errors != pattern was used
    # TODO: Implement stricter signal before production
    return True
```

---

### Phase 3: Dynamic Curriculum (2 hours)
**Goal**: Adapt curriculum sequence to learner needs

#### 3.1 Pattern Dependency Graph
```python
class PatternDependency:
    """
    Define relationships between grammar patterns.

    Example:
    - "accusative_case" requires "definite_articles_nominative"
    - "subordinate_clause_verb_final" requires "sv_order_main_clause"
    """
    pattern: str
    requires: List[str]  # prerequisites
    enables: List[str]  # patterns this unlocks
    difficulty_impact: float  # how much harder patterns become if this not mastered

# Build dependency graph for German grammar
PATTERN_DEPENDENCIES = {
    "accusative_case": {
        "requires": ["definite_articles_nominative"],
        "enables": ["dative_case", "two_way_prepositions"],
    },
    "subordinate_clause_verb_final": {
        "requires": ["sv_order_main_clause"],
        "enables": ["relative_clauses", "separable_verbs_in_clauses"],
    },
    # ... etc
}
```

#### 3.2 Adaptive Curriculum Ordering
```python
def get_adaptive_curriculum_order(self, learner: Learner) -> List[str]:
    """
    Generate personalized curriculum order based on learner needs.

    Algorithm:
    1. Start with base A1 → B1 sequence
    2. Identify learner's weak areas
    3. Move related patterns earlier for reinforcement
    4. Identify learner's strengths
    5. Move advanced dependent patterns earlier (they can handle it)
    6. Respect prerequisites
    7. Maximize learning efficiency
    """
    base_order = [p.name for p in self.GERMAN_GRAMMAR_CURRICULUM]

    # Get learner profile
    weaknesses = self.learner_profile.error_prone_patterns
    strengths = self.learner_profile.strength_patterns

    # Reorder based on needs
    adaptive_order = self._reorder_for_reinforcement(
        base_order, weaknesses
    )
    adaptive_order = self._reorder_for_acceleration(
        adaptive_order, strengths
    )

    # Validate prerequisites still satisfied
    adaptive_order = self._validate_dependencies(adaptive_order)

    return adaptive_order

def _reorder_for_reinforcement(
    self,
    order: List[str],
    weaknesses: List[str]
) -> List[str]:
    """
    Move related patterns earlier for extra practice.

    If learner struggles with "case", move all case patterns earlier
    and add more spacing between them for practice.

    IMPLEMENTATION: Rule-based category prioritization

    ALGORITHM:
    1. Extract categories from weaknesses (e.g., "accusative_case" → "case")
    2. Find all patterns in weak categories
    3. Group them by category
    4. Move each weak category earlier in sequence
    5. Insert review patterns between weak category patterns
    """
    if not weaknesses:
        return order

    # Step 1: Extract weak categories from pattern names
    weak_categories = set()
    for pattern_name in weaknesses:
        category = self._get_pattern_category(pattern_name)
        weak_categories.add(category)

    # Step 2: Find all patterns in weak categories
    weak_category_patterns = {cat: [] for cat in weak_categories}
    other_patterns = []

    for pattern_name in order:
        pattern = self._pattern_map.get(pattern_name)
        if pattern and pattern.category.value in weak_categories:
            weak_category_patterns[pattern.category.value].append(pattern_name)
        else:
            other_patterns.append(pattern_name)

    # Step 3: Build new order with weak categories first
    new_order = []

    # Add weak category patterns early (with spacing for review)
    for category, patterns in weak_category_patterns.items():
        # Move this category's patterns to front
        for pattern_name in patterns:
            new_order.append(pattern_name)
            # Add spacing pattern after every weak category pattern
            # This allows for practice and reinforcement
            if len(new_order) % 3 == 0:  # Every 3rd position
                # Add a brief review/work pattern from other categories
                if other_patterns:
                    new_order.append(other_patterns.pop(0))

    # Add remaining patterns
    new_order.extend(other_patterns)

    return new_order

def _get_pattern_category(self, pattern_name: str) -> str:
    """
    Get category for a pattern (for grouping related patterns).

    IMPLEMENTATION: Lookup from curriculum definition
    """
    pattern = self._pattern_map.get(pattern_name)
    if pattern:
        return pattern.category.value
    return "general"
```

---

### Phase 4: Proactive Teaching (2 hours)
**Goal**: Teach grammar BEFORE errors occur

#### 4.1 Predictive Teaching
```python
def should_proactively_teach(self, context: Dict) -> Optional[Dict]:
    """
    Decide if we should teach grammar before errors occur.

    Scenarios:
    1. Topic introduces new grammar → teach pattern first
    2. Prerequisite mastered → teach next pattern
    3. Review due → schedule practice
    4. Pattern combination coming → teach interaction
    """
    conversation_topic = context.get("topic")

    # Check if topic requires specific grammar
    required_patterns = self._get_grammar_for_topic(conversation_topic)

    for pattern_name in required_patterns:
        learner_pattern = self.learner.grammar_patterns.get(pattern_name)

        # If not introduced, this is a good time!
        if learner_pattern is None:
            return {
                "action": "introduce_pattern",
                "pattern": pattern_name,
                "reason": f"Topic '{conversation_topic}' uses this grammar",
                "timing": "before_topic",
            }

        # If weak, review first
        if learner_pattern.mastery_score < 0.6:
            return {
                "action": "review_pattern",
                "pattern": pattern_name,
                "reason": f"Topic '{conversation_topic}' uses this grammar",
                "timing": "before_topic",
            }

    return None

def _get_grammar_for_topic(self, topic: str) -> List[str]:
    """
    Map conversation topics to required grammar patterns.

    Example:
    "daily routine" → ["separable_verbs_basic", "present_tense_regular"]
    "past events" → ["perfect_tense_haben", "perfect_tense_sein"]
    "describing things" → ["adjective_endings_basic", "noun_gender"]

    IMPLEMENTATION: Hybrid approach (static cache + LLM fallback)

    APPROACH:
    1. Check static topic-to-grammar mapping (cache)
    2. If not found, use LLM to determine relevant grammar
    3. Cache LLM result for future use
    """
    # Check cache first
    topic_lower = topic.lower().strip()
    if topic_lower in self._topic_grammar_cache:
        return self._topic_grammar_cache[topic_lower]

    # LLM fallback for unknown topics
    prompt = f"""Given the conversation topic "{topic}", which German grammar patterns from this list are most relevant?

Available patterns:
{', '.join([p.name for p in self.GERMAN_GRAMMAR_CURRICULUM[:20]])}

Return only the pattern names, separated by commas, most relevant first."""

    try:
        response = self.llm_client.generate_response(
            system_prompt="You are a German language pedagogy expert.",
            user_message=prompt,
            max_tokens=100
        )

        # Parse response and return valid pattern names
        suggested_patterns = [p.strip() for p in response.split(',')]
        valid_patterns = [p for p in suggested_patterns if p in self._pattern_map]

        # Cache the result (persists across calls)
        if valid_patterns:
            self._topic_grammar_cache[topic_lower] = valid_patterns

        return valid_patterns[:5]  # Top 5 most relevant

    except Exception:
        # Fallback to empty list on error
        return []
```

#### 4.2 Teaching Triggers
```python
def _get_teaching_triggers(self, context: Dict) -> List[Dict]:
    """
    Identify all reasons we might want to teach grammar NOW.

    Returns prioritized list of teaching opportunities.

    IMPLEMENTATION: Check multiple trigger types and prioritize
    """
    triggers = []

    # 1. Review due (spaced repetition)
    due_patterns = self._get_patterns_due_for_review()
    for pattern in due_patterns:
        triggers.append({
            "type": "review_due",
            "pattern": pattern,
            "priority": 0.9,
        })

    # 2. Recent recurring errors
    recurring = self._get_recurring_errors()
    for pattern in recurring:
        triggers.append({
            "type": "recurring_error",
            "pattern": pattern,
            "priority": 0.8,
        })

    # 3. Prerequisite mastered → teach next
    next_pattern = self._get_next_unlocked_pattern()
    if next_pattern:
        triggers.append({
            "type": "prerequisite_ready",
            "pattern": next_pattern,
            "priority": 0.7,
        })

    # 4. Topic-relevant grammar (context parameter passed in)
    context_triggers = self.should_proactively_teach(context)
    if context_triggers:
        triggers.append(context_triggers)

    # Sort by priority
    triggers.sort(key=lambda t: t["priority"], reverse=True)

    return triggers
```

---

### Phase 5: Context-Aware Decision Making (2 hours)
**Goal**: Make smart decisions about when to teach

#### 5.1 Teaching Timing Model
```python
def should_teach_now(self, trigger: Dict, context: Dict) -> bool:
    """
    Strategic decision: Is THIS the right moment?

    Consider multiple factors with priority-based overrides.

    IMPLEMENTATION: Layered decision making with early exits

    ALGORITHM:
    1. Check hard constraints (flow, confidence) - return False if fail
    2. Check timing constraints (frequency) - return False if too soon
    3. For high-priority triggers: use relaxed thresholds
    4. For normal-priority triggers: use standard thresholds
    5. Check learner receptiveness and natural fit
    """
    flow_score = context.get("flow_score", 0.5)
    confidence = context.get("confidence", ConfidenceLevel.MEDIUM)
    priority = trigger.get("priority", 0.5)

    # Hard constraint: Don't overwhelm VERY_LOW confidence learners
    # (Cannot be overridden even by high priority)
    if confidence == ConfidenceLevel.VERY_LOW:
        return False

    # Hard constraint: Don't teach if flow is extremely poor (< 0.3)
    # (Cannot be overridden - conversation is struggling)
    if flow_score < 0.3:
        return False

    # High-priority triggers (review due, recurring errors) get relaxed thresholds
    if priority >= 0.9:
        # Can proceed with flow >= 0.3 (already checked above)
        # Skip frequency check for urgent reviews
        pass
    else:
        # Standard-priority triggers need better flow
        if flow_score < 0.5:  # Standard threshold
            return False

        # Check teaching frequency (don't teach too often)
        turns_since_grammar = self._turns_since_last_grammar_teaching(context)
        if turns_since_grammar < 10:
            return False

    # Check if learner is receptive
    if not self._is_learner_receptive(context):
        return False

    # Check if this fits naturally in conversation
    if not self._fits_conversation_naturally(trigger, context):
        return False

    return True

def _is_learner_receptive(self, context: Dict) -> bool:
    """
    Is the learner in a good state to learn grammar?

    Signs of receptiveness:
    - Asking questions
    - Recent successful turns
    - Not showing frustration
    - Making attempt to use grammar

    IMPLEMENTATION: Rule-based signal detection

    ALGORITHM:
    1. Check recent learner inputs for questions (contains '?')
    2. Check recent success rate (errors in last 5 turns)
    3. Check for frustration signals (repeated errors, short responses)
    4. Calculate aggregate receptiveness score
    """
    recent_turns = context.get("recent_turns", [])
    if len(recent_turns) < 3:
        return True  # Not enough data, assume receptive

    # Signal 1: Asking questions (positive)
    question_count = sum(1 for turn in recent_turns[-5:] if '?' in turn.get("learner_input", ""))
    if question_count >= 1:
        return True  # Learner is engaged!

    # Signal 2: Recent success rate
    recent_errors = sum(turn.get("error_count", 0) for turn in recent_turns[-5:])
    if recent_errors == 0:
        return True  # Doing well, ready for new material

    # Signal 3: Frustration detection
    avg_response_length = sum(len(turn.get("learner_input", "")) for turn in recent_turns[-5:]) / 5
    if avg_response_length < 10:  # Very short responses
        if recent_errors > 3:
            return False  # Likely frustrated

    # Signal 4: Attempting grammar (even if errors)
    grammar_attempts = sum(1 for turn in recent_turns[-3:] if turn.get("error_count", 0) > 0)
    if grammar_attempts >= 2 and recent_errors < 5:
        return True  # Trying, but not overwhelmed

    # Default: cautiously receptive
    return True

#### 5.2 Natural Integration
```python
def _fits_conversation_naturally(
    self,
    trigger: Dict,
    context: Dict
) -> bool:
    """
    Can this grammar be introduced naturally?

    Check:
    - Does conversation topic relate?
    - Did learner just use related grammar?
    - Are there examples in recent context?

    PRIORITY BYPASS: High-priority triggers skip this check
    - Review due (spaced repetition): Always teach, topic-independent
    - Recurring errors: Always teach, topic-independent
    - Lower-priority triggers: Require natural fit

    RATIONALE: Reviews and recurring error corrections are time-sensitive
    and shouldn't be suppressed just because the topic doesn't match.
    """
    priority = trigger.get("priority", 0.5)

    # High-priority triggers bypass natural fit check
    if priority >= 0.8:
        return True  # Teach regardless of topic fit

    topic = context.get("topic", "")

    # Get topic-relevant patterns
    topic_patterns = self._get_grammar_for_topic(topic)

    if trigger["pattern"] in topic_patterns:
        return True  # Natural fit!

    # Check if learner just used related pattern
    recent_patterns = self._get_recent_patterns_used(context)
    trigger_category = self._get_pattern_category(trigger["pattern"])

    for recent_pattern in recent_patterns:
        if self._are_patterns_related(recent_pattern, trigger_category):
            return True

    return False
```

---

## 🔧 Implementation Details

### New Models to Create

```python
# src/models/grammar_teaching.py

class TeachingStrategyTracker(BaseModel):
    """Track which teaching strategies work for this learner."""
    strategies: Dict[str, StrategyStats] = {}

class LearnerGrammarProfile(BaseModel):
    """Profile of this learner's grammar learning."""
    learning_style: str = "unknown"
    error_prone_patterns: List[str] = []
    strength_patterns: List[str] = []
    effective_methods: List[str] = []
    ineffective_methods: List[str] = []
    avg_mastery_time: float = 0.0

    def update_from_teaching_result(
        self,
        pattern: str,
        strategy: str,
        success: bool,
        pattern_mastery_data: Optional[Dict] = None
    ):
        """
        Update profile based on teaching effectiveness.

        IMPLEMENTATION: Track patterns and strategies

        Args:
            pattern: Pattern name that was taught
            strategy: Teaching strategy used
            success: Whether the teaching was effective
            pattern_mastery_data: Optional dict with pattern stats {
                "attempts": int,
                "mastery_score": float
            }
        """
        if success:
            if strategy not in self.effective_methods:
                self.effective_methods.append(strategy)
            if strategy in self.ineffective_methods:
                self.ineffective_methods.remove(strategy)

            # Track strength patterns (mastered quickly)
            # pattern_mastery_data is passed in from the agent, which has access to learner.grammar_patterns
            if pattern_mastery_data:
                attempts = pattern_mastery_data.get("attempts", 0)
                mastery_score = pattern_mastery_data.get("mastery_score", 0.0)

                if attempts <= 3 and mastery_score >= 0.7:
                    if pattern not in self.strength_patterns:
                        self.strength_patterns.append(pattern)
        else:
            if strategy not in self.ineffective_methods and len(self.effective_methods) > 0:
                # Only mark as ineffective if we have comparison data
                if strategy not in self.effective_methods:
                    self.ineffective_methods.append(strategy)

            # Track error-prone patterns
            if pattern not in self.error_prone_patterns:
                self.error_prone_patterns.append(pattern)

class PatternDependencyGraph(BaseModel):
    """Dependencies between grammar patterns."""
    dependencies: Dict[str, List[str]] = {}
    enables: Dict[str, List[str]] = {}
```

### LLM Prompts to Design

#### 1. Teaching Decision Prompt
```
You are a pedagogical grammar expert. Decide what grammar teaching action to take.

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
1. INTRODUCE_PATTERN: Teach new grammar pattern
2. REVIEW_PATTERN: Practice due pattern
3. REINFORCE_PATTERN: Strengthen weak pattern
4. WAIT: Don't interrupt conversation

Decide and explain your reasoning.
```

#### 2. Teaching Approach Prompt
```
You are generating a teaching approach for the pattern: {pattern_name}

Pattern Details:
- Category: {category}
- Difficulty: {difficulty}
- Description: {description}

Learner Profile:
- Learning style: {learning_style}
- Effective methods: {effective_methods}
- Past struggles with this pattern: {struggles}

Generate a teaching approach and return ONLY valid JSON in this format:
{
    "strategy": "explicit_explanation" | "pattern_highlighting" | "guided_discovery",
    "explanation": "2-3 sentence explanation appropriate for {learning_style} learners",
    "examples": ["example1", "example2", "example3"],
    "practice_suggestion": "Simple exercise or question for learner"
}

Ensure the explanation matches the learner's learning style.
```

#### 3. Learner Profiling Prompt
```
You are analyzing this learner's grammar learning patterns.

Recent Grammar Interactions:
{interactions}

Determine:
1. Learning style (analytical | visual | immersion)
2. Most effective teaching methods
3. Patterns they struggle with
4. Patterns they excel at
5. Optimal teaching frequency

Return ONLY valid JSON in this format:
{
    "learning_style": "analytical" | "visual" | "immersion" | "unknown",
    "effective_methods": ["method1", "method2"],
    "struggle_patterns": ["pattern1", "pattern2"],
    "strength_patterns": ["pattern1", "pattern2"],
    "optimal_frequency": "every_X_turns"
}
```

---

## 📊 Success Metrics

### Quantitative Metrics
1. **Grammar Mastery Rate**: % of patterns mastered (target: >70%)
2. **Error Reduction**: Decrease in grammar errors over time (target: -40%)
3. **Teaching Effectiveness**: % of teaching that leads to improvement (target: >60%)
4. **Learner Engagement**: Turns with active grammar practice (target: >30%)
5. **Retention Rate**: Patterns still mastered after 1 week (target: >80%)

### Qualitative Metrics
1. **Natural Conversation Integration**: Does grammar teaching flow naturally?
2. **Learner Confidence**: Does learner feel supported, not overwhelmed?
3. **Personalization**: Is teaching adapted to individual learning style?
4. **Proactivity**: Does agent teach before errors become habits?

---

## 🎯 Implementation Checklist

### Phase 1: Foundation (2 hours)
- [ ] Add LLM client initialization to `__init__`
- [ ] Create `_build_teaching_context()` method
- [ ] Create `_generate_teaching_plan()` with LLM call + JSON schema
- [ ] Implement `_rule_based_teaching_decision()` fallback
- [ ] Add `_load_teaching_state()` and `_save_teaching_state()` methods
- [ ] Rewrite `process()` as agentic ReAct loop with persistence
- [ ] Add `_execute_teaching_plan()` method
- [ ] Test basic LLM decision-making and fallback behavior

### Phase 2: Learning (3 hours)
- [ ] Create `src/models/grammar_teaching.py`
- [ ] Implement `TeachingStrategyTracker` class
- [ ] Implement `LearnerGrammarProfile` class with Pydantic BaseModel
- [ ] Add `update_learning_style()` method to profile (NOT LLM call!)
- [ ] Add persistence field to Learner model: `grammar_teaching_state: Optional[Dict] = None`
- [ ] Add `_track_teaching_effectiveness()` method with pending action pattern
- [ ] Add `_detect_learning_style()` method in agent with throttling
- [ ] Implement strategy effectiveness tracking
- [ ] Document effectiveness measurement limitations
- [ ] Test learning and adaptation with persistence restarts

### Phase 4: Proactive Teaching (2 hours)
- [ ] Implement `should_proactively_teach()`
- [ ] Create topic-to-grammar mapping with class-level cache
- [ ] Implement `_get_teaching_triggers()`
- [ ] Implement `_get_patterns_due_for_review()`
- [ ] Implement `_get_next_unlocked_pattern()`
- [ ] Test proactive teaching

### Phase 5: Context Awareness (2 hours)
- [ ] Implement `should_teach_now()` with priority-based overrides
- [ ] Implement `_is_learner_receptive()` with signal detection
- [ ] Implement `_fits_conversation_naturally()` with high-priority bypass
- [ ] Implement `_turns_since_last_grammar_teaching()`
- [ ] Fine-tune timing thresholds
- [ ] Test context-aware decisions

### Phase 3: Dynamic Curriculum (2 hours)
- [ ] Create pattern dependency graph
- [ ] Implement `get_adaptive_curriculum_order()`
- [ ] Implement `_reorder_for_reinforcement()` with category grouping
- [ ] Implement `_reorder_for_acceleration()` for strength-based advancement
- [ ] Implement `_validate_dependencies()` to ensure prerequisites met
- [ ] Test curriculum adaptation with learner profiles

**Note**: Phase 3 is done last because it requires a working `LearnerGrammarProfile` from Phase 2 to make intelligent reordering decisions. Phases 4 and 5 provide more immediate value and can be developed in parallel with the learning system.

### Testing & Integration (2 hours)
- [ ] Write unit tests for new methods
- [ ] Integration test with ConversationAgent
- [ ] End-to-end test with simulated learner
- [ ] Tune LLM prompts
- [ ] Adjust thresholds based on testing
- [ ] Documentation updates

---

## 💡 Key Design Patterns

### 1. Agentic ReAct Loop
```python
def process(self, input_data):
    context = self.perceive(input_data)
    decision = self.reason(context)
    result = self.act(decision)
    self.reflect(result, context)
    self.adapt(result)
    return result
```

### 2. Strategy Pattern with Learning
```python
# Try different strategies, learn what works
strategy = self.select_best_strategy(pattern)
result = self.execute_strategy(strategy, pattern)
self.track_effectiveness(strategy, result)
```

### 3. Dependency Graph
```python
# Respect learning dependencies
if not self.check_prerequisites(pattern):
    return self.teach_prerequisite_first(pattern)
```

### 4. Adaptive Sequencing
```python
# Personalize curriculum order
order = base_order
order = self.reorder_for_learner_needs(order)
order = self.validate_dependencies(order)
```

---

## 🚀 Getting Started

### Step 1: Setup (15 min)
```bash
# Create new models file
touch src/models/grammar_teaching.py

# Create prompts file
touch src/llm/grammar_prompts.py

# Run tests to ensure baseline works
pytest tests/test_grammar_curriculum.py -v
```

### Step 2: First Agentic Feature (45 min)
Implement LLM-driven teaching decision:

```python
# In grammar_curriculum.py

def _generate_teaching_plan(self, context: Dict) -> Dict:
    """First agentic feature!"""
    prompt = f"""
    You are a grammar pedagogy expert.

    Learner context:
    {context['learner_state']}

    Conversation context:
    {context['conversation']}

    Decide what to do: INTRODUCE, REVIEW, or WAIT?
    """

    response = self.llm_client.generate_response(
        system_prompt="You are a pedagogical expert...",
        user_message=prompt,
        response_format="json"
    )

    return json.loads(response)
```

### Step 3: Test and Iterate (30 min)
```bash
# Run the app and observe behavior
python -m src

# Check logs for LLM decisions
# Adjust prompt if decisions aren't good
```

---

## 📚 Reference Materials

### Files to Study
- [src/agents/conversation.py](../src/agents/conversation.py) - Agentic ReAct pattern (lines 92-229)
- [src/agents/grammar_curriculum.py](../src/agents/grammar_curriculum.py) - Current implementation
- [src/models/grammar.py](../src/models/grammar.py) - Grammar pattern model
- [docs/pronunciation_agent_plan_learning.md](./pronunciation_agent_plan_learning.md) - Similar agent implementation

### Related Concepts
- **ReAct Prompting**: Reasoning + Acting pattern for LLM agents
- **Spaced Repetition**: SM-2 algorithm for review scheduling
- **Pedagogical Strategies**: When to correct vs when to let flow
- **Dependency Graphs**: Prerequisite relationships in learning

---

## 🎓 Learning Outcomes

After completing this upgrade, you'll understand:

1. **Agentic Design**: How to build autonomous AI agents
2. **LLM Decision-Making**: Using LLMs for strategic reasoning
3. **Learning Systems**: Building agents that improve over time
4. **Adaptive Curriculum**: Personalizing learning sequences
5. **Context-Aware AI**: Making decisions based on multiple factors
6. **Multi-Agent Coordination**: How grammar agent fits in larger system

---

## ⚠️ Challenges & Solutions

### Challenge 1: LLM Decision Quality
**Problem**: LLM might make poor teaching decisions
**Solution**:
- Start with guardrails (validate LLM decisions)
- Provide clear JSON schema in prompts with response_format="json"
- Track decision quality and adjust prompts
- **Implemented**: Rule-based fallback when LLM fails (Phase 1)
  - `_rule_based_teaching_decision()` uses highest-priority trigger
  - Logs fallback events for monitoring
  - Ensures system never crashes due to LLM failure

### Challenge 2: Overwhelming Learner
**Problem**: Too much grammar teaching interrupts conversation
**Solution**:
- Conservative teaching frequency (every 10-15 turns)
- High threshold for flow score (>0.4)
- Priority-based decision making
- "Wait" is a valid decision!

### Challenge 3: Learning from Noise
**Problem**: Learner improvements might not be from our teaching
**Solution**:
- Track multiple metrics, not just next-turn success
- Look for patterns over time, not single instances
- Use statistical significance testing
- A/B test different approaches

**Persistence Consideration**: All learning is saved to `learner.grammar_teaching_state` and persisted via MemoryStore. This ensures:
- Long-term tracking across sessions (days/weeks)
- No loss of learner insights on restart
- Ability to analyze learning patterns over time
- Data-driven refinement of teaching strategies

### Challenge 4: LLM Call Volume and Cost
**Problem**: At full build-out, a single turn could trigger multiple LLM calls:
1. Teaching decision (every turn with errors)
2. Teaching approach generation (when teaching)
3. Learning style detection (throttled: every 50 turns)
4. Topic-to-grammar mapping (cached after first LLM call per topic)

**Solution**:
- **Throttling**: Learning style detection runs every 50 turns (configurable)
- **Caching**: Topic-to-grammar mappings cached at class level (persist across sessions)
- **Fallback**: Rule-based decisions when LLM fails (reduces retry attempts)
- **Batching potential**: Multiple teaching decisions could be batched in future

**Cost Estimate** (Claude Sonnet, typical session):
- Teaching decision: ~500 tokens × $0.003/1K = ~$0.0015 per call
- Teaching approach: ~300 tokens × $0.003/1K = ~$0.0009 per call
- Learning style: ~400 tokens × $0.003/1K = ~$0.0012 per call
- **Per 100-turn session**: ~$0.15-0.30 (assuming 20-30 teaching moments)
- **Mitigation**: Caching and throttling reduce this by ~60%

### Challenge 5: Effectiveness Measurement Accuracy
**Problem**: `_check_pattern_usage_in_current_turn()` has a logic gap
- Returns True if no errors in category
- Doesn't confirm learner actually attempted the pattern
- May overestimate teaching effectiveness

**Solution**:
- **Documented limitation**: Prominent warning in code comments
- **Recommended**: Implement stricter signal before production
  - Check learner input for grammar-specific tokens
  - Track explicit practice attempts
  - Use multi-turn window with decay
- **Monitor**: Track strategy success rates for anomalies
- **Iterate**: Refine measurement based on real usage data

### Challenge 4: Complexity
**Problem**: System becomes complex and hard to debug
**Solution**:
- Extensive logging of decisions and reasoning
- Metrics dashboard for monitoring
- Unit tests for each component
- Gradual rollout (feature flags)

---

## 🔄 Iterative Development Approach

### Start Simple
1. Add LLM decision-making (Phase 1)
2. Test and refine prompts
3. Add learning (Phase 2)
4. Add proactive teaching (Phase 4)
5. Add context awareness (Phase 5)
6. Add dynamic curriculum (Phase 3)

**Note on Phase Ordering**: Phase 3 (Dynamic Curriculum) is done last because it requires a working LearnerGrammarProfile from Phase 2 to make intelligent reordering decisions. Phases 4 and 5 provide more immediate value and can be developed in parallel with the learning system.

### Test Each Phase
Before moving to next phase, ensure:
- Decisions are reasonable
- Learner experience is positive
- No regressions in existing functionality
- Performance is acceptable

### Get Feedback
- Observe agent decisions in real conversations
- Ask learners about experience
- Monitor metrics over time
- Adjust based on data

---

## 📝 Next Steps

1. **Review this plan** with questions or clarifications
2. **Set up development environment** (15 min)
3. **Start Phase 1**: Add LLM integration (2 hours)
4. **Test basic agentic behavior** (30 min)
5. **Continue with remaining phases**

**Total Time Estimate**: 12-15 hours for full implementation

**Phase breakdown**:
- Phase 1 (Foundation): 2 hours
- Phase 2 (Learning): 3 hours
- Phase 3 (Dynamic Curriculum): 2 hours
- Phase 4 (Proactive Teaching): 2 hours
- Phase 5 (Context Awareness): 2 hours
- Testing & Integration: 2 hours
- **Total**: 13 hours + 1 hour buffer = 14 hours

**Recommended Pace**: 2-3 hours per session over 1 week

---

**Ready to build an agentic grammar curriculum agent? Let's start with Phase 1! 🚀**
