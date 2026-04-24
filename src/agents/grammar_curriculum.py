"""
Grammar curriculum agent for progressive grammar instruction.

This agent manages a structured curriculum of grammar patterns for German
learners, tracking which patterns have been introduced and determining when
the learner is ready to advance to more complex patterns.

PHASE 1 UPGRADE: Now with LLM integration for agentic decision-making.
"""

import json
from typing import Any, Dict, List, Optional, ClassVar
from dataclasses import dataclass, asdict
from datetime import datetime

from .base import Agent, AgentConfig
from models.grammar import GrammarWeakness
from models.grammar_teaching import StrategyStats, LearnerGrammarProfile
from models.learner import ConfidenceLevel


@dataclass
class CurriculumPattern:
    """A grammar pattern in the curriculum."""
    name: str  # Pattern identifier (e.g., "present_regular")
    category: GrammarWeakness  # Type of weakness/category
    difficulty_level: int  # 1-5
    introduced_at_level: str  # CEFR level (A1, A2, B1)
    description: str  # Brief description


class GrammarCurriculumAgent(Agent):
    """
    Agent for managing grammar curriculum and pattern tracking.

    This agent:
    - Defines an ordered curriculum of German grammar patterns (A1 -> B1)
    - Routes errors to the correct GrammarPattern with proper metadata
    - Tracks learner progress through the curriculum
    - Determines when learner is ready to advance
    """

    # Class-level constant: ordered grammar curriculum for German A1 -> B1
    GERMAN_GRAMMAR_CURRICULUM: List[CurriculumPattern] = [
        # === A1 LEVEL: Basic Foundations ===
        # Start with most fundamental patterns - verb in second position
        CurriculumPattern(
            name="sv_order_main_clause",
            category=GrammarWeakness.WORD_ORDER,
            difficulty_level=1,
            introduced_at_level="A1",
            description="Subject-Verb order in main clauses (verb always 2nd position)"
        ),
        # Basic present tense - most fundamental
        CurriculumPattern(
            name="present_tense_regular",
            category=GrammarWeakness.VERB_CONJUGATION,
            difficulty_level=1,
            introduced_at_level="A1",
            description="Present tense of regular verbs (ich spiele, du spielst)"
        ),
        # Essential for basic sentences
        CurriculumPattern(
            name="definite_articles_nominative",
            category=GrammarWeakness.ARTICLE_USAGE,
            difficulty_level=1,
            introduced_at_level="A1",
            description="Definite articles in nominative (der, die, das)"
        ),
        # Noun gender is fundamental
        CurriculumPattern(
            name="noun_gender",
            category=GrammarWeakness.GENDER,
            difficulty_level=1,
            introduced_at_level="A1",
            description="Noun gender recognition (masculine, feminine, neuter)"
        ),
        # Questions are essential early
        CurriculumPattern(
            name="question_word_order",
            category=GrammarWeakness.WORD_ORDER,
            difficulty_level=1,
            introduced_at_level="A1",
            description="Question word order (verb first in yes/no questions)"
        ),
        # Basic separable verbs appear early
        CurriculumPattern(
            name="separable_verbs_basic",
            category=GrammarWeakness.SEPARABLE_VERB,
            difficulty_level=2,
            introduced_at_level="A1",
            description="Basic separable prefix verbs (aufstehen, mitkommen)"
        ),
        # Accusative is first case
        CurriculumPattern(
            name="accusative_case",
            category=GrammarWeakness.CASE,
            difficulty_level=2,
            introduced_at_level="A1",
            description="Accusative case for direct objects (den, die, das, einen)"
        ),
        # Indefinite articles
        CurriculumPattern(
            name="indefinite_articles_nominative",
            category=GrammarWeakness.ARTICLE_USAGE,
            difficulty_level=2,
            introduced_at_level="A1",
            description="Indefinite articles in nominative (ein, eine, ein)"
        ),
        # Perfect tense introduction
        CurriculumPattern(
            name="perfect_tense_haben",
            category=GrammarWeakness.PERFECT_TENSE,
            difficulty_level=2,
            introduced_at_level="A1",
            description="Present perfect with 'haben' for most verbs"
        ),

        # === A2 LEVEL: Intermediate Patterns ===
        # Dative case
        CurriculumPattern(
            name="dative_case",
            category=GrammarWeakness.CASE,
            difficulty_level=3,
            introduced_at_level="A2",
            description="Dative case for indirect objects (dem, der, dem, einem)"
        ),
        # Preposition + case
        CurriculumPattern(
            name="prepositions_accusative",
            category=GrammarWeakness.PREPOSITION,
            difficulty_level=3,
            introduced_at_level="A2",
            description="Prepositions always taking accusative (durch, fur, gegen)"
        ),
        # Modal verbs
        CurriculumPattern(
            name="modal_verbs_present",
            category=GrammarWeakness.VERB_CONJUGATION,
            difficulty_level=3,
            introduced_at_level="A2",
            description="Modal verbs in present tense (konnen, mussen, wollen)"
        ),
        # Subordinate clauses
        CurriculumPattern(
            name="subordinate_clause_verb_final",
            category=GrammarWeakness.SUBORDINATE_CLAUSE,
            difficulty_level=3,
            introduced_at_level="A2",
            description="Verb in final position in subordinate clauses (weil, dass)"
        ),
        # Adjective endings
        CurriculumPattern(
            name="adjective_endings_basic",
            category=GrammarWeakness.ADJECTIVE_ENDING,
            difficulty_level=3,
            introduced_at_level="A2",
            description="Basic adjective endings after definite articles"
        ),
        # More prepositions
        CurriculumPattern(
            name="prepositions_dative",
            category=GrammarWeakness.PREPOSITION,
            difficulty_level=3,
            introduced_at_level="A2",
            description="Prepositions always taking dative (aus, bei, mit, nach)"
        ),
        # Two-way prepositions
        CurriculumPattern(
            name="two_way_prepositions",
            category=GrammarWeakness.PREPOSITION,
            difficulty_level=3,
            introduced_at_level="A2",
            description="Prepositions taking accusative or dative (in, an, auf)"
        ),
        # Perfect with sein
        CurriculumPattern(
            name="perfect_tense_sein",
            category=GrammarWeakness.PERFECT_TENSE,
            difficulty_level=3,
            introduced_at_level="A2",
            description="Present perfect with 'sein' for motion verbs"
        ),

        # === B1 LEVEL: Advanced Patterns ===
        # Genitive case
        CurriculumPattern(
            name="genitive_case",
            category=GrammarWeakness.CASE,
            difficulty_level=4,
            introduced_at_level="B1",
            description="Genitive case for possession (des, der, des, eines)"
        ),
        # Passive voice
        CurriculumPattern(
            name="passive_present",
            category=GrammarWeakness.PASSIVE_VOICE,
            difficulty_level=4,
            introduced_at_level="B1",
            description="Passive voice in present tense (werden + participle)"
        ),
        # Complex subordinate clauses
        CurriculumPattern(
            name="relative_clauses",
            category=GrammarWeakness.SUBORDINATE_CLAUSE,
            difficulty_level=4,
            introduced_at_level="B1",
            description="Relative clauses with correct case endings"
        ),
        # Advanced adjective endings
        CurriculumPattern(
            name="adjective_endings_all",
            category=GrammarWeakness.ADJECTIVE_ENDING,
            difficulty_level=4,
            introduced_at_level="B1",
            description="Adjective endings after all determiners and in all positions"
        ),
        # Advanced separable verbs
        CurriculumPattern(
            name="separable_verbs_in clauses",
            category=GrammarWeakness.SEPARABLE_VERB,
            difficulty_level=4,
            introduced_at_level="B1",
            description="Separable verbs in subordinate clauses and questions"
        ),
        # Future tense
        CurriculumPattern(
            name="future_tense",
            category=GrammarWeakness.VERB_CONJUGATION,
            difficulty_level=4,
            introduced_at_level="B1",
            description="Future tense with 'werden' + infinitive"
        ),
    ]

    @classmethod
    def get_valid_pattern_names(cls) -> List[str]:
        """
        Get list of all valid pattern names from the curriculum.

        This class method provides the valid pattern names for use in prompts,
        without requiring an instance of the agent.

        Returns:
            List of valid pattern names that should be used in error analysis
        """
        return [pattern.name for pattern in cls.GERMAN_GRAMMAR_CURRICULUM]

    # Class-level cache for topic-to-grammar mapping (shared across instances)
    # DESIGN DECISION: This is intentionally a ClassVar (shared across all learners)
    # - Static entries are language-specific, not learner-specific (safe to share)
    # - LLM-generated entries are also shared (intentional: topic→grammar mapping is universal)
    # - Reduces redundant LLM calls across learners
    # - Trade-off: One learner's topics benefit all learners (acceptable)
    _topic_grammar_cache: ClassVar[Dict[str, List[str]]] = {
        "daily routine": ["separable_verbs_basic", "present_tense_regular"],
        "past events": ["perfect_tense_haben", "perfect_tense_sein"],
        "describing things": ["adjective_endings_basic", "noun_gender"],
        "family": ["definite_articles_nominative", "possessive_articles"],
        "food": ["accusative_case", "indefinite_articles_nominative"],
        "directions": ["prepositions_accusative", "two_way_prepositions"],
        "future plans": ["future_tense", "modal_verbs_present"],
    }

    #
    # CONCURRENCY NOTE: If this system moves to multi-user server context,
    # this shared mutable class variable could become a race condition.
    # Before deploying to concurrent environments, replace ClassVar cache
    # with thread-safe LRU cache (e.g., functools.lru_cache with threading.Lock).

    def __init__(
        self,
        config: AgentConfig,
        learner,
        llm_client=None,
    ):
        """
        Initialize the grammar curriculum agent.

        Args:
            config: Agent configuration
            learner: Learner state
            llm_client: LLM client for agentic decision-making
        """
        super().__init__(config, learner, llm_client)

        # Build lookup maps for efficient pattern finding
        self._pattern_map = {p.name: p for p in self.GERMAN_GRAMMAR_CURRICULUM}
        self._patterns_by_level = self._build_level_index()
        self._patterns_by_category = self._build_category_index()

        # Phase 1: Teaching state (for learning and adaptation)
        # Track what works for THIS learner
        self.teaching_strategy_tracker: Dict[str, StrategyStats] = {}
        self.learner_profile = LearnerGrammarProfile()

        # Track pending teaching actions to evaluate effectiveness on next turn
        # PERSISTENCE: This is saved in _save_teaching_state() to survive process restarts
        self._pending_teaching_action: Optional[Dict] = None

        # Learning style detection: cache and throttle
        self._learning_style_detection_turns: int = 0
        self._learning_style_detection_interval: int = 50  # Detect every 50 turns

        # Teaching timing tracking
        self._last_grammar_teaching_turn: int = 0

    def _build_level_index(self) -> Dict[str, List[CurriculumPattern]]:
        """Build an index of patterns by CEFR level."""
        index = {"A1": [], "A2": [], "B1": [], "B2": []}
        for pattern in self.GERMAN_GRAMMAR_CURRICULUM:
            level = pattern.introduced_at_level
            if level in index:
                index[level].append(pattern)
        return index

    def _build_category_index(self) -> Dict[GrammarWeakness, List[CurriculumPattern]]:
        """Build an index of patterns by category."""
        index = {category: [] for category in GrammarWeakness}
        for pattern in self.GERMAN_GRAMMAR_CURRICULUM:
            index[pattern.category].append(pattern)
        return index

    def _build_teaching_context(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build comprehensive teaching context for LLM decision-making.

        Gathers all relevant information about the learner, conversation,
        and grammar state to inform teaching decisions.

        Args:
            input_data: Input data containing errors and conversation context

        Returns:
            Comprehensive context dictionary for LLM reasoning
        """
        errors = input_data.get("errors", [])
        learner_input = input_data.get("learner_input", "")

        # Extract recent errors for weaknesses analysis
        recent_errors = [e for e in errors if e.get("type") == "grammar"]
        weaknesses = [e.get("pattern", "unknown") for e in recent_errors]

        # Get mastered patterns
        mastered_patterns = {
            name: pattern.mastery_score
            for name, pattern in self.learner.grammar_patterns.items()
            if pattern.mastery_score >= 0.7
        }

        # Build learner state summary
        learner_state = {
            "cefr_level": self.learner.current_cefr_level,
            "confidence": self.learner.confidence.value,
            "recent_errors": weaknesses[-5:] if weaknesses else [],  # Last 5 errors
            "mastered_patterns": mastered_patterns,
            "weaknesses": weaknesses,
            "total_patterns_learned": len(self.learner.grammar_patterns),
        }

        # Build conversation context
        conversation_context = {
            "topic": input_data.get("topic", "general"),
            "flow_score": input_data.get("flow_score", 0.5),
            "recent_input": learner_input,
            "turns_since_last_grammar": self._turns_since_last_grammar_teaching(input_data),
        }

        return {
            "learner_state": learner_state,
            "conversation": conversation_context,
            "errors": errors,
            "available_patterns": [p.name for p in self.GERMAN_GRAMMAR_CURRICULUM],
        }

    def _turns_since_last_grammar_teaching(self, input_data: Dict[str, Any]) -> int:
        """
        Calculate turns since last grammar teaching moment.

        Args:
            input_data: Input data containing turn information

        Returns:
            Number of turns since last grammar teaching
        """
        current_turn = input_data.get("turn_number", 0)
        return current_turn - self._last_grammar_teaching_turn

    def _generate_teaching_plan(self, context: Dict) -> Dict:
        """
        Use LLM to decide what grammar to teach and how.

        This is the core "REASON" step in the agentic ReAct loop.
        The LLM analyzes the context and decides what teaching action to take.

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
            # LLM-based decision
            return self._llm_teaching_decision(context)
        except Exception as e:
            print(f"[GrammarCurriculum] LLM decision failed ({e}), using fallback")
            return self._rule_based_teaching_decision(context)

    def _llm_teaching_decision(self, context: Dict) -> Dict:
        """
        LLM-driven teaching decision with proper JSON schema.

        Returns structured JSON dict with action, pattern, reasoning, etc.

        Args:
            context: Teaching context from _build_teaching_context()

        Returns:
            Structured teaching decision from LLM
        """
        learner_state = context["learner_state"]
        conversation = context["conversation"]

        prompt = f"""You are a pedagogical grammar expert. Decide what grammar teaching action to take.

Learner State:
- Level: {learner_state['cefr_level']}
- Confidence: {learner_state['confidence']}
- Recent errors: {learner_state['recent_errors']}
- Mastered patterns: {list(learner_state['mastered_patterns'].keys())}
- Current weaknesses: {learner_state['weaknesses']}

Conversation Context:
- Topic: {conversation['topic']}
- Flow score: {conversation['flow_score']} (0.0 = struggling, 1.0 = flowing)
- Recent learner input: {conversation['recent_input']}
- Turns since last grammar teaching: {conversation['turns_since_last_grammar']}

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

        if not self.llm_client:
            raise ValueError("LLM client not available")

        response = self.llm_client.generate_response(
            system_prompt="You are a German grammar pedagogy expert. Always respond with valid JSON only, no additional text.",
            user_message=prompt,
            temperature=0.3,  # Lower temperature for more structured output
            max_tokens=200,
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

        Args:
            context: Teaching context from _build_teaching_context()

        Returns:
            Rule-based teaching decision
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
        """
        Map trigger type to action string.

        Args:
            trigger_type: Type of teaching trigger

        Returns:
            Corresponding action string
        """
        mapping = {
            "review_due": "review_pattern",
            "recurring_error": "reinforce_pattern",
            "prerequisite_ready": "introduce_pattern",
        }
        return mapping.get(trigger_type, "wait")

    def _get_teaching_triggers(self, context: Dict) -> List[Dict]:
        """
        Identify all reasons we might want to teach grammar NOW.

        Returns prioritized list of teaching opportunities.

        IMPLEMENTATION: Check multiple trigger types and prioritize

        Args:
            context: Teaching context

        Returns:
            List of teaching triggers, sorted by priority
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
        recurring = self._get_recurring_errors(context)
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

        # Sort by priority
        triggers.sort(key=lambda t: t["priority"], reverse=True)

        return triggers

    def _get_patterns_due_for_review(self) -> List[str]:
        """
        Get patterns that are due for spaced repetition review.

        Returns:
            List of pattern names due for review
        """
        due_patterns = []
        for name, pattern in self.learner.grammar_patterns.items():
            if pattern.needs_review:
                due_patterns.append(name)
        return due_patterns

    def _get_recurring_errors(self, context: Dict) -> List[str]:
        """
        Get patterns with recurring errors from recent context.

        Args:
            context: Teaching context

        Returns:
            List of pattern names with recurring errors
        """
        recent_errors = context["learner_state"]["recent_errors"]
        # Count error frequency
        error_counts = {}
        for pattern_name in recent_errors:
            error_counts[pattern_name] = error_counts.get(pattern_name, 0) + 1

        # Return patterns with 2+ errors
        return [pattern for pattern, count in error_counts.items() if count >= 2]

    def _get_next_unlocked_pattern(self) -> Optional[str]:
        """
        Get the next pattern whose prerequisites are mastered.

        Returns:
            Pattern name that can be introduced, or None
        """
        # This is a simplified version - in full implementation,
        # would check actual prerequisite dependencies
        return self.get_next_pattern()

    def _load_teaching_state(self) -> None:
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

            print("[GrammarCurriculum] Teaching state loaded successfully")

    def _save_teaching_state(self) -> None:
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

        # Note: MemoryStore.save_learner() will be called by ConversationAgent
        # or the main application loop

    def _execute_teaching_plan(self, teaching_plan: Dict, context: Dict) -> Dict:
        """
        Execute a teaching plan decided by LLM or rule-based logic.

        This is the "ACT" step in the agentic ReAct loop.

        Args:
            teaching_plan: Teaching plan from _generate_teaching_plan()
            context: Teaching context

        Returns:
            Result dictionary with execution outcomes
        """
        action = teaching_plan["action"]
        pattern = teaching_plan.get("pattern")

        result = {
            "action": action,
            "pattern": pattern,
            "reasoning": teaching_plan.get("reasoning", ""),
            "teaching_approach": teaching_plan.get("teaching_approach", "none"),
            "executed": False,
        }

        if action == "wait":
            result["executed"] = True
            result["message"] = "Continuing conversation flow"
            return result

        if not pattern:
            result["executed"] = False
            result["message"] = f"Action {action} requires a pattern"
            return result

        # Execute the teaching action
        if action == "introduce_pattern":
            success = self._introduce_pattern(pattern, teaching_plan, context)
        elif action == "review_pattern":
            success = self._review_pattern(pattern, teaching_plan, context)
        elif action == "reinforce_pattern":
            success = self._reinforce_pattern(pattern, teaching_plan, context)
        else:
            success = False
            result["message"] = f"Unknown action: {action}"

        result["executed"] = success
        if success:
            # Update last grammar teaching turn
            self._last_grammar_teaching_turn = context["conversation"].get("turns_since_last_grammar", 0)

        return result

    def _introduce_pattern(self, pattern_name: str, teaching_plan: Dict, context: Dict) -> bool:
        """
        Introduce a new grammar pattern.

        Args:
            pattern_name: Name of pattern to introduce
            teaching_plan: Teaching plan with approach and examples
            context: Teaching context

        Returns:
            True if successful
        """
        # Check if pattern exists in curriculum
        curriculum_pattern = self._pattern_map.get(pattern_name)
        if not curriculum_pattern:
            print(f"[GrammarCurriculum] Unknown pattern: {pattern_name}")
            return False

        # Create pattern on learner if it doesn't exist
        if pattern_name not in self.learner.grammar_patterns:
            from models.grammar import GrammarPattern
            self.learner.grammar_patterns[pattern_name] = GrammarPattern(
                name=curriculum_pattern.name,
                description=curriculum_pattern.description,
                category=curriculum_pattern.category,
                difficulty_level=curriculum_pattern.difficulty_level,
                introduced_at_level=curriculum_pattern.introduced_at_level,
            )
            print(f"[GrammarCurriculum] Introduced pattern: {pattern_name}")
            return True

        return False

    def _review_pattern(self, pattern_name: str, teaching_plan: Dict, context: Dict) -> bool:
        """
        Review an existing grammar pattern.

        Args:
            pattern_name: Name of pattern to review
            teaching_plan: Teaching plan with approach and examples
            context: Teaching context

        Returns:
            True if successful
        """
        if pattern_name not in self.learner.grammar_patterns:
            print(f"[GrammarCurriculum] Cannot review unknown pattern: {pattern_name}")
            return False

        # Record a review attempt (not counted as success/failure yet)
        # The actual learning will be measured in next turns
        print(f"[GrammarCurriculum] Reviewed pattern: {pattern_name}")
        return True

    def _reinforce_pattern(self, pattern_name: str, teaching_plan: Dict, context: Dict) -> bool:
        """
        Reinforce a weak grammar pattern.

        Args:
            pattern_name: Name of pattern to reinforce
            teaching_plan: Teaching plan with approach and examples
            context: Teaching context

        Returns:
            True if successful
        """
        if pattern_name not in self.learner.grammar_patterns:
            print(f"[GrammarCurriculum] Cannot reinforce unknown pattern: {pattern_name}")
            return False

        # Record a reinforcement attempt
        print(f"[GrammarCurriculum] Reinforced pattern: {pattern_name}")
        return True

    def get_capabilities(self) -> List[str]:
        """Return what this agent can do."""
        return [
            "manage structured grammar curriculum (A1 -> B1)",
            "route grammar errors to correct pattern with metadata",
            "track learner progress through curriculum",
            "determine readiness to advance to next pattern",
            "suggest next focus pattern based on mastery",
        ]

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        AGENTIC VERSION: ReAct loop for grammar teaching.

        This method implements the full agentic pattern:
        1. PERCEIVE: Gather context
        2. REASON: LLM decides what to do
        3. ACT: Teach/Review/Assess/Wait
        4. REFLECT: Track effectiveness (placeholder for Phase 2)
        5. UPDATE: Modify learner state

        Args:
            input_data: Dictionary containing:
                - errors: List of error dicts from analyze_learner_input
                - learner_input: What the learner said (optional)
                - topic: Current conversation topic (optional)
                - flow_score: Conversation flow score (optional)
                - turn_number: Current turn number (optional)

        Returns:
            Dictionary with:
                - action: Action taken (introduce_pattern, review_pattern, etc.)
                - pattern: Pattern involved (if any)
                - patterns_updated: List of pattern names that were updated
                - ready_to_advance: bool indicating if learner can advance
                - suggested_focus: Next pattern to focus on (if any)
                - current_position: Current position in curriculum
                - reasoning: Why this action was taken
        """
        # Load persisted teaching state on first call
        if not self.teaching_strategy_tracker and not self.learner_profile.learning_style:
            self._load_teaching_state()

        # Step 1: PERCEIVE - Gather context
        context = self._build_teaching_context(input_data)

        # Step 2: REASON - LLM decides what to do (with fallback)
        teaching_plan = self._generate_teaching_plan(context)

        # Step 3: ACT - Execute the decision
        result = self._execute_teaching_plan(teaching_plan, context)

        # Step 4: LEGACY ERROR TRACKING - Still process errors for compatibility
        errors = input_data.get("errors", [])
        patterns_updated = self._process_errors(errors)

        # Step 5: REFLECT - Track effectiveness (placeholder for Phase 2)
        # In Phase 2, this will call _track_teaching_effectiveness()
        # For now, we just log the action
        print(f"[GrammarCurriculum] Action: {result['action']}, Pattern: {result.get('pattern', 'N/A')}")

        # Step 6: UPDATE - Save teaching state for persistence
        self._save_teaching_state()

        # Get curriculum status
        ready_to_advance = self.is_ready_to_advance()
        suggested_focus = self.get_next_pattern()
        current_position = self._get_current_position()

        return {
            "action": result["action"],
            "pattern": result.get("pattern"),
            "patterns_updated": patterns_updated,
            "ready_to_advance": ready_to_advance,
            "suggested_focus": suggested_focus,
            "current_position": current_position,
            "reasoning": result.get("reasoning", ""),
        }

    def _process_errors(self, errors: List[Dict]) -> List[str]:
        """
        Process grammar errors and update learner state.

        This maintains backward compatibility with the original reactive behavior.

        Args:
            errors: List of error dicts

        Returns:
            List of pattern names that were updated
        """
        patterns_updated = []

        for error in errors:
            if error.get("type") != "grammar":
                continue

            # Get the pattern name from the error (or use category fallback)
            pattern_name = error.get("pattern", "")
            if not pattern_name:
                # Fallback to category name if pattern not specified
                category = error.get("category", "general")
                pattern_name = category

            # Find curriculum definition for this pattern
            curriculum_pattern = self._pattern_map.get(pattern_name)

            # Determine success based on error severity
            # If Claude detected an error, it wasn't successful
            success = error.get("severity") not in ["moderate", "major"]

            # Get or create the GrammarPattern on the learner
            if pattern_name not in self.learner.grammar_patterns:
                # Create with proper metadata from curriculum
                if curriculum_pattern:
                    from models.grammar import GrammarPattern
                    self.learner.grammar_patterns[pattern_name] = GrammarPattern(
                        name=curriculum_pattern.name,
                        description=curriculum_pattern.description,
                        category=curriculum_pattern.category,
                        difficulty_level=curriculum_pattern.difficulty_level,
                        introduced_at_level=curriculum_pattern.introduced_at_level,
                    )
                else:
                    # Unknown pattern - create with defaults based on category
                    from models.grammar import GrammarPattern
                    # Try to infer category from name
                    category = self._infer_category(pattern_name)
                    self.learner.grammar_patterns[pattern_name] = GrammarPattern(
                        name=pattern_name,
                        description=f"Grammar pattern: {pattern_name}",
                        category=category,
                        difficulty_level=2,  # Default to intermediate
                        introduced_at_level=self.learner.current_cefr_level,
                    )

            # Record the attempt
            pattern = self.learner.grammar_patterns[pattern_name]
            pattern.record_attempt(success)
            patterns_updated.append(pattern_name)

        return patterns_updated

    def _infer_category(self, pattern_name: str) -> GrammarWeakness:
        """
        Infer category from pattern name for unknown patterns.

        Args:
            pattern_name: Name of the pattern

        Returns:
            Inferred GrammarWeakness category
        """
        name_lower = pattern_name.lower()

        # Check for category keywords in pattern name
        if "verb" in name_lower or "tense" in name_lower:
            return GrammarWeakness.VERB_CONJUGATION
        elif "case" in name_lower:
            return GrammarWeakness.CASE
        elif "article" in name_lower:
            return GrammarWeakness.ARTICLE_USAGE
        elif "gender" in name_lower:
            return GrammarWeakness.GENDER
        elif "order" in name_lower:
            return GrammarWeakness.WORD_ORDER
        elif "preposition" in name_lower or "prep" in name_lower:
            return GrammarWeakness.PREPOSITION
        elif "adjective" in name_lower:
            return GrammarWeakness.ADJECTIVE_ENDING
        elif "clause" in name_lower or "subordinate" in name_lower:
            return GrammarWeakness.SUBORDINATE_CLAUSE
        elif "separable" in name_lower:
            return GrammarWeakness.SEPARABLE_VERB
        elif "perfect" in name_lower or "passive" in name_lower:
            return GrammarWeakness.PERFECT_TENSE

        # Default fallback
        return GrammarWeakness.WORD_ORDER

    def _get_current_position(self) -> Dict[str, Any]:
        """
        Get learner's current position in the curriculum.

        Returns:
            Dict with level, index, and current pattern info
        """
        learner_level = self.learner.current_cefr_level

        # Count mastered patterns at each level
        mastered_count = 0
        current_level_patterns = self._patterns_by_level.get(learner_level, [])
        total_level_patterns = len(current_level_patterns)

        for pattern in current_level_patterns:
            learner_pattern = self.learner.grammar_patterns.get(pattern.name)
            if learner_pattern and learner_pattern.mastery_score >= 0.7:
                mastered_count += 1

        return {
            "level": learner_level,
            "patterns_mastered": mastered_count,
            "total_patterns_at_level": total_level_patterns,
            "progress_percent": round(mastered_count / max(total_level_patterns, 1) * 100, 1),
        }

    def get_next_pattern(self) -> Optional[str]:
        """
        Get the next pattern the learner should focus on.

        Returns the next GrammarPattern from the curriculum that the learner
        has not yet mastered, respecting the learner's current CEFR level.

        Returns:
            Name of the next pattern to focus on, or None if all appropriate patterns mastered
        """
        learner_level = self.learner.current_cefr_level

        # Determine which levels are accessible
        level_order = ["A1", "A2", "B1"]
        accessible_levels = []

        for level in level_order:
            accessible_levels.append(level)
            if level == learner_level:
                break

        # Search through accessible levels for next pattern
        for level in accessible_levels:
            patterns_at_level = self._patterns_by_level.get(level, [])

            for pattern in patterns_at_level:
                learner_pattern = self.learner.grammar_patterns.get(pattern.name)

                # If pattern doesn't exist or isn't mastered, it's a candidate
                if learner_pattern is None:
                    return pattern.name

                if learner_pattern.mastery_score < 0.7:
                    return pattern.name

        # All patterns at accessible levels are mastered
        return None

    def is_ready_to_advance(self) -> bool:
        """
        Determine if learner is ready to advance in the curriculum.

        Returns True if the learner's mastery_score on the current focus
        pattern is above 0.7 AND they have attempted it at least 5 times.

        Returns:
            True if ready to advance to next pattern
        """
        # Get the current focus pattern
        suggested_focus = self.get_next_pattern()

        if suggested_focus is None:
            return False

        pattern = self.learner.grammar_patterns.get(suggested_focus)

        if pattern is None:
            # Pattern hasn't been introduced yet - not ready to advance FROM it
            return False

        # Check mastery score and attempt count
        return pattern.mastery_score >= 0.7 and pattern.attempts >= 5

    def get_introduced_patterns(self) -> List[str]:
        """
        Get list of patterns that have been introduced to this learner.

        Returns:
            List of pattern names that exist in learner's grammar_patterns
        """
        return list(self.learner.grammar_patterns.keys())

    def get_curriculum_overview(self) -> Dict[str, Any]:
        """
        Get overview of the entire curriculum with learner's progress.

        Returns:
            Dict with curriculum organized by level and progress
        """
        overview = {}

        for level in ["A1", "A2", "B1"]:
            patterns = self._patterns_by_level.get(level, [])
            level_data = []

            for pattern in patterns:
                learner_pattern = self.learner.grammar_patterns.get(pattern.name)
                progress = {
                    "name": pattern.name,
                    "description": pattern.description,
                    "category": pattern.category.value,
                    "difficulty": pattern.difficulty_level,
                    "introduced": learner_pattern is not None,
                }

                if learner_pattern:
                    progress.update({
                        "mastery_score": round(learner_pattern.mastery_score, 2),
                        "attempts": learner_pattern.attempts,
                        "error_rate": round(learner_pattern.error_rate, 2),
                    })

                level_data.append(progress)

            overview[level] = level_data

        return overview
