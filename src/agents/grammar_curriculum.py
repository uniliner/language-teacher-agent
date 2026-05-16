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
from llm.grammar_prompts import (
    TEACHING_DECISION_SYSTEM_PROMPT,
    TEACHING_DECISION_USER_PROMPT_TEMPLATE,
    TEACHING_APPROACH_SYSTEM_PROMPT,
    TEACHING_APPROACH_USER_PROMPT_TEMPLATE,
    LEARNER_PROFILING_SYSTEM_PROMPT,
    LEARNER_PROFILING_USER_PROMPT_TEMPLATE,
    TOPIC_GRAMMAR_SYSTEM_PROMPT,
    TOPIC_GRAMMAR_USER_PROMPT_TEMPLATE,
    TEACHING_DECISION_PARAMS,
    TEACHING_APPROACH_PARAMS,
    LEARNER_PROFILING_PARAMS,
    TOPIC_GRAMMAR_PARAMS,
    build_teaching_decision_prompt,
    build_teaching_approach_prompt,
    build_learner_profiling_prompt,
    build_topic_grammar_prompt,
    get_prompt_version,
)


@dataclass
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

    # Build dependency graph for German grammar
    # This defines which patterns are prerequisites for others
    PATTERN_DEPENDENCIES: Dict[str, PatternDependency] = {
        "sv_order_main_clause": PatternDependency(
            pattern="sv_order_main_clause",
            requires=[],
            enables=["subordinate_clause_verb_final", "question_word_order"],
            difficulty_impact=0.8,
        ),
        "definite_articles_nominative": PatternDependency(
            pattern="definite_articles_nominative",
            requires=[],
            enables=["accusative_case", "dative_case", "adjective_endings_basic"],
            difficulty_impact=0.9,
        ),
        "noun_gender": PatternDependency(
            pattern="noun_gender",
            requires=[],
            enables=["adjective_endings_basic", "adjective_endings_all"],
            difficulty_impact=0.7,
        ),
        "accusative_case": PatternDependency(
            pattern="accusative_case",
            requires=["definite_articles_nominative"],
            enables=["dative_case", "two_way_prepositions"],
            difficulty_impact=0.8,
        ),
        "present_tense_regular": PatternDependency(
            pattern="present_tense_regular",
            requires=[],
            enables=["perfect_tense_haben", "modal_verbs_present", "future_tense"],
            difficulty_impact=0.9,
        ),
        "separable_verbs_basic": PatternDependency(
            pattern="separable_verbs_basic",
            requires=["present_tense_regular"],
            enables=["separable_verbs_in_clauses"],
            difficulty_impact=0.6,
        ),
        "question_word_order": PatternDependency(
            pattern="question_word_order",
            requires=["sv_order_main_clause"],
            enables=[],
            difficulty_impact=0.3,
        ),
        "indefinite_articles_nominative": PatternDependency(
            pattern="indefinite_articles_nominative",
            requires=["definite_articles_nominative"],
            enables=[],
            difficulty_impact=0.2,
        ),
        "perfect_tense_haben": PatternDependency(
            pattern="perfect_tense_haben",
            requires=["present_tense_regular"],
            enables=["perfect_tense_sein", "passive_present"],
            difficulty_impact=0.7,
        ),
        "dative_case": PatternDependency(
            pattern="dative_case",
            requires=["definite_articles_nominative", "accusative_case"],
            enables=["genitive_case", "two_way_prepositions"],
            difficulty_impact=0.8,
        ),
        "prepositions_accusative": PatternDependency(
            pattern="prepositions_accusative",
            requires=["accusative_case"],
            enables=["two_way_prepositions"],
            difficulty_impact=0.6,
        ),
        "modal_verbs_present": PatternDependency(
            pattern="modal_verbs_present",
            requires=["present_tense_regular"],
            enables=[],
            difficulty_impact=0.5,
        ),
        "subordinate_clause_verb_final": PatternDependency(
            pattern="subordinate_clause_verb_final",
            requires=["sv_order_main_clause"],
            enables=["relative_clauses", "separable_verbs_in_clauses"],
            difficulty_impact=0.9,
        ),
        "adjective_endings_basic": PatternDependency(
            pattern="adjective_endings_basic",
            requires=["definite_articles_nominative", "noun_gender"],
            enables=["adjective_endings_all"],
            difficulty_impact=0.7,
        ),
        "prepositions_dative": PatternDependency(
            pattern="prepositions_dative",
            requires=["dative_case"],
            enables=["two_way_prepositions"],
            difficulty_impact=0.6,
        ),
        "two_way_prepositions": PatternDependency(
            pattern="two_way_prepositions",
            requires=["accusative_case", "dative_case"],
            enables=[],
            difficulty_impact=0.8,
        ),
        "perfect_tense_sein": PatternDependency(
            pattern="perfect_tense_sein",
            requires=["perfect_tense_haben"],
            enables=[],
            difficulty_impact=0.5,
        ),
        "genitive_case": PatternDependency(
            pattern="genitive_case",
            requires=["dative_case"],
            enables=[],
            difficulty_impact=0.6,
        ),
        "passive_present": PatternDependency(
            pattern="passive_present",
            requires=["perfect_tense_haben"],
            enables=[],
            difficulty_impact=0.7,
        ),
        "relative_clauses": PatternDependency(
            pattern="relative_clauses",
            requires=["subordinate_clause_verb_final"],
            enables=[],
            difficulty_impact=0.8,
        ),
        "adjective_endings_all": PatternDependency(
            pattern="adjective_endings_all",
            requires=["adjective_endings_basic"],
            enables=[],
            difficulty_impact=0.9,
        ),
        "separable_verbs_in_clauses": PatternDependency(
            pattern="separable_verbs_in_clauses",
            requires=["separable_verbs_basic", "subordinate_clause_verb_final"],
            enables=[],
            difficulty_impact=0.7,
        ),
        "future_tense": PatternDependency(
            pattern="future_tense",
            requires=["present_tense_regular"],
            enables=[],
            difficulty_impact=0.6,
        ),
    }

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
        # NOTE: Each agent instance has its own tracker (learner-specific)
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

        #
        # CONCURRENCY NOTE: teaching_strategy_tracker is instance-specific (per learner),
        # unlike _topic_grammar_cache which is shared across all learners.
        # This design avoids race conditions in multi-user scenarios for learner-specific data.

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

        Note: Uses centralized prompts from llm.grammar_prompts for versioning.
        """
        learner_state = context["learner_state"]
        conversation = context["conversation"]

        # Build user prompt using centralized template
        user_prompt = TEACHING_DECISION_USER_PROMPT_TEMPLATE.format(
            cefr_level=learner_state['cefr_level'],
            confidence=learner_state['confidence'],
            recent_errors=learner_state['recent_errors'],
            mastered_patterns=list(learner_state['mastered_patterns'].keys()),
            weaknesses=learner_state['weaknesses'],
            topic=conversation['topic'],
            flow_score=conversation['flow_score'],
            learner_input=conversation['recent_input']
        )

        if not self.llm_client:
            raise ValueError("LLM client not available")

        response = self.llm_client.generate_response(
            system_prompt=TEACHING_DECISION_SYSTEM_PROMPT,
            user_message=user_prompt,
            **TEACHING_DECISION_PARAMS
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

        STRATEGY: Use teaching triggers with Phase 4 timing evaluation

        Args:
            context: Teaching context from _build_teaching_context()

        Returns:
            Rule-based teaching decision with timing awareness
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

        # Evaluate triggers in priority order until we find one that's suitable NOW
        for trigger in triggers:
            # Phase 4: Check if THIS is the right moment to teach
            if self.should_teach_now(trigger, context):
                return {
                    "action": self._map_trigger_type_to_action(trigger["type"]),
                    "pattern": trigger["pattern"],
                    "reasoning": f"Rule-based: {trigger['type']} ({trigger.get('reason', 'Priority: {:.1f}'.format(trigger['priority']))})",
                    "teaching_approach": "explicit_explanation",  # Default for fallback
                    "examples_needed": True,
                    "priority": trigger["priority"],
                }

        # No suitable teaching moment found - timing matters!
        return {
            "action": "wait",
            "pattern": None,
            "reasoning": "Teaching triggers found but NOW is not the right moment (timing evaluation)",
            "teaching_approach": "none",
            "examples_needed": False,
            "priority": 0.0,
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
            # Phase 4: Topic-based triggers
            "topic_relevant_introduction": "introduce_pattern",
            "topic_relevant_review": "review_pattern",
            "topic_relevant": "introduce_pattern",  # Default for topic triggers
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

        # 4. Topic-relevant grammar (Phase 4: Context-Aware Teaching)
        context_triggers = self.should_proactively_teach(context)
        if context_triggers:
            # Map action to trigger type
            action_to_trigger_type = {
                "introduce_pattern": "topic_relevant_introduction",
                "review_pattern": "topic_relevant_review",
            }
            triggers.append({
                "type": action_to_trigger_type.get(context_triggers["action"], "topic_relevant"),
                "pattern": context_triggers["pattern"],
                "priority": context_triggers.get("priority", 0.6),
                "reason": context_triggers.get("reason", ""),
            })

        # Sort by priority
        triggers.sort(key=lambda t: t["priority"], reverse=True)

        return triggers

    def should_teach_now(self, trigger: Dict, context: Dict) -> bool:
        """
        Strategic decision: Is THIS the right moment to teach?

        This is the core Phase 4 timing logic that determines whether to interrupt
        conversation flow for grammar teaching. It considers multiple factors with
        priority-based overrides to balance pedagogical effectiveness with
        natural conversation flow.

        Args:
            trigger: Teaching trigger with 'pattern', 'priority', and optional 'reason'
            context: Teaching context containing flow, confidence, recent turns

        Returns:
            True if teaching should proceed, False otherwise

        IMPLEMENTATION: Layered decision making with early exits

        ALGORITHM:
        1. Check hard constraints (flow, confidence) - return False if fail
        2. Check timing constraints (frequency) - return False if too soon
        3. For high-priority triggers: use relaxed thresholds
        4. For normal-priority triggers: use standard thresholds
        5. Check learner receptiveness and natural fit
        """
        flow_score = context.get("flow_score", 0.5)
        confidence = context.get("confidence", ConfidenceLevel.MODERATE)
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

            # **TEACHING FREQUENCY BYPASS** (design decision, not a bug):
            # Spaced-repetition reviews and recurring error corrections are TIME-SENSITIVE.
            # They bypass the 10-turn frequency check because:
            # 1. Reviews are scheduled based on memory decay (not arbitrary frequency)
            # 2. Recurring errors indicate forming bad habits (urgent correction needed)
            # 3. Waiting risks fossilizing errors or missing review windows
            # This is pedagogically sound and intentional behavior.
            pass
        else:
            # Standard-priority triggers need better flow
            if flow_score < 0.5:  # Standard threshold
                return False

            # Check teaching frequency (don't teach too often)
            # Get turns_since_last_grammar from either direct context or conversation sub-context
            turns_since_grammar = context.get("turns_since_last_grammar",
                                              context.get("conversation", {}).get("turns_since_last_grammar", 0))

            # Use learner's optimal teaching frequency (detected via LLM)
            required_turns = self._get_optimal_teaching_frequency()
            if turns_since_grammar < required_turns:
                return False

        # Check if learner is receptive
        if not self._is_learner_receptive(context):
            return False

        # Check if this fits naturally in conversation
        if not self._fits_conversation_naturally(trigger, context):
            return False

        return True

    def _get_optimal_teaching_frequency(self) -> int:
        """
        Get the optimal teaching frequency for this learner.

        Parses the `optimal_teaching_frequency` from the learner profile
        and returns the number of turns to wait between grammar lessons.

        Returns:
            Number of turns (default: 10)

        Examples:
            - "every_8_turns" -> 8
            - "every_10_turns" -> 10
            - "every_15_turns" -> 15
            - "adaptive" -> 10 (default)
        """
        frequency_str = self.learner_profile.optimal_teaching_frequency

        # Parse the frequency string to extract the number
        # Format: "every_X_turns" where X is a number
        if frequency_str and frequency_str != "adaptive":
            try:
                # Extract the number from strings like "every_10_turns"
                # Split by underscore and find the numeric part
                parts = frequency_str.split('_')
                for part in parts:
                    if part.isdigit():
                        return int(part)
            except (ValueError, AttributeError):
                pass

        # Default to 10 turns if we can't parse or it's "adaptive"
        return 10

    def _is_learner_receptive(self, context: Dict) -> bool:
        """
        Is the learner in a good state to learn grammar?

        Signs of receptiveness:
        - Asking questions
        - Recent successful turns
        - Not showing frustration
        - Making attempt to use grammar

        Args:
            context: Teaching context with recent turns and conversation history

        Returns:
            True if learner appears receptive to grammar teaching

        IMPLEMENTATION: Rule-based signal detection with aggregate scoring

        ALGORITHM:
        1. Check recent learner inputs for questions (contains '?')
        2. Check recent success rate (errors in last 5 turns)
        3. Check for frustration signals (repeated errors, short responses)
        4. Check for grammar attempts (engagement despite errors)
        5. Calculate aggregate receptiveness score (range: -2 to +4)
        6. Return True if score >= threshold (1.0)

        KEY CHANGE: Frustration signals can now override positive signals.
        Previous early-exit pattern prevented this - now using aggregate scoring.
        """
        recent_turns = context.get("recent_turns", [])
        if len(recent_turns) < 3:
            return True  # Not enough data, assume receptive

        receptiveness_score = 0.0

        # Signal 1: Asking questions (strong positive: +2)
        question_count = sum(1 for turn in recent_turns[-5:] if '?' in turn.get("learner_input", ""))
        if question_count >= 1:
            receptiveness_score += 2.0  # Learner is engaged!

        # Signal 2: Recent success rate (positive: +1)
        recent_errors = sum(turn.get("error_count", 0) for turn in recent_turns[-5:])
        if recent_errors == 0:
            receptiveness_score += 1.0  # Doing well, ready for new material

        # Signal 3: Frustration detection (strong negative: -2)
        avg_response_length = sum(len(turn.get("learner_input", "")) for turn in recent_turns[-5:]) / 5
        if avg_response_length < 10:  # Very short responses
            if recent_errors > 3:
                receptiveness_score -= 2.0  # Likely frustrated

        # Signal 4: Attempting grammar (positive: +1)
        grammar_attempts = sum(1 for turn in recent_turns[-3:] if turn.get("error_count", 0) > 0)
        if grammar_attempts >= 2 and recent_errors < 5:
            receptiveness_score += 1.0  # Trying, but not overwhelmed

        # Return True if aggregate score is positive
        # Threshold of 1.0 means learner needs more positive than negative signals
        return receptiveness_score >= 1.0

    def _fits_conversation_naturally(self, trigger: Dict, context: Dict) -> bool:
        """
        Can this grammar be introduced naturally in current conversation?

        Check:
        - Does conversation topic relate?
        - Did learner just use related grammar?
        - Are there examples in recent context?

        Args:
            trigger: Teaching trigger with pattern information
            context: Teaching context with conversation topic and recent patterns

        Returns:
            True if teaching fits naturally in conversation

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

        topic = context.get("conversation", {}).get("topic", "")
        if not topic:
            return False

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

    def _get_recent_patterns_used(self, context: Dict) -> List[str]:
        """
        Get list of grammar patterns used in recent conversation turns.

        Args:
            context: Teaching context with recent turns

        Returns:
            List of pattern names used recently
        """
        recent_turns = context.get("recent_turns", [])
        patterns_used = []

        for turn in recent_turns[-5:]:  # Last 5 turns
            patterns = turn.get("grammar_patterns_used", [])
            patterns_used.extend(patterns)

        return list(set(patterns_used))  # Remove duplicates

    def _are_patterns_related(self, pattern1: str, category2: str) -> bool:
        """
        Check if two grammar patterns are related.

        Two patterns are related if they belong to the same category or
        if one enables the other (based on dependencies).

        Args:
            pattern1: First pattern name
            category2: Category of second pattern

        Returns:
            True if patterns are related
        """
        # Get category of first pattern
        category1 = self._get_pattern_category(pattern1)

        # Same category = related
        if category1 == category2:
            return True

        # Check if patterns have enabling relationship
        # This is a simplified version - full implementation would check PATTERN_DEPENDENCIES
        return False

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

    def _get_grammar_for_topic(self, topic: str) -> List[str]:
        """
        Get relevant grammar patterns for a conversation topic.

        Uses a hybrid approach:
        1. Check static cache first (common topics)
        2. If not found, use LLM to determine relevant grammar
        3. Cache LLM result for future use

        Args:
            topic: Conversation topic (e.g., "food", "daily routine")

        Returns:
            List of grammar pattern names relevant to this topic

        Design Notes:
            - Checks cache first to avoid redundant LLM calls
            - Uses LLM to determine grammar patterns for unknown topics
            - Caches empty results to prevent repeated LLM calls for topics with no grammar mapping
            - Returns cached results (including empty lists) to prevent retry loops

        Note: Uses centralized prompts from llm.grammar_prompts for versioning.
        """
        # Check cache first (including failed lookups)
        topic_lower = topic.lower().strip()
        if topic_lower in self._topic_grammar_cache:
            cached = self._topic_grammar_cache[topic_lower]
            # Empty list sentinel means "we checked, no patterns found"
            return cached if cached != [] else []

        # LLM fallback for unknown topics
        if self.llm_client is None:
            return []  # No LLM available, return empty list

        try:
            # Build prompt using centralized template
            available_patterns = ', '.join([p.name for p in self.GERMAN_GRAMMAR_CURRICULUM[:20]])
            system_prompt, user_prompt = build_topic_grammar_prompt(topic, available_patterns)

            # Use Haiku for fast, cheap topic-to-grammar mapping
            # Direct API call to use specific model (not generate_response)
            response = self.llm_client.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=TOPIC_GRAMMAR_PARAMS["max_tokens"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )

            # Parse response and return valid pattern names
            response_text = response.content[0].text
            suggested_patterns = [p.strip() for p in response_text.split(',')]
            valid_patterns = [p for p in suggested_patterns if p in self._pattern_map]

            # Cache the result (persists across calls)
            if valid_patterns:
                self._topic_grammar_cache[topic_lower] = valid_patterns
            else:
                # Cache empty result to prevent repeated LLM calls for topics with no grammar mapping
                self._topic_grammar_cache[topic_lower] = []

            return valid_patterns[:5]  # Top 5 most relevant

        except Exception:
            # Fallback to empty list on error
            # Cache empty result to prevent retry loops
            self._topic_grammar_cache[topic_lower] = []
            return []

    def should_proactively_teach(self, context: Dict) -> Optional[Dict]:
        """
        Decide if we should teach grammar before errors occur based on conversation topic.

        This method implements topic-based proactive teaching by identifying patterns
        that are relevant to the current conversation topic and checking if the learner
        needs them introduced or reinforced.

        Scenarios:
        1. Topic introduces new grammar → teach pattern first
        2. Topic uses grammar learner is weak in → review first
        3. No grammar needs for topic → return None

        Args:
            context: Teaching context containing conversation topic and learner state

        Returns:
            Dict with teaching action if needed, None otherwise:
            {
                "action": "introduce_pattern" | "review_pattern",
                "pattern": "pattern_name",
                "reason": "Topic '{topic}' uses this grammar",
                "timing": "before_topic",
                "priority": 0.6  # Medium priority for topic-based teaching
            }
        """
        conversation_topic = context.get("conversation", {}).get("topic", "")
        if not conversation_topic:
            return None

        # Check if topic requires specific grammar
        required_patterns = self._get_grammar_for_topic(conversation_topic)
        if not required_patterns:
            return None

        # Check each required pattern
        for pattern_name in required_patterns:
            learner_pattern = self.learner.grammar_patterns.get(pattern_name)

            # If not introduced, this is a good time!
            if learner_pattern is None:
                return {
                    "action": "introduce_pattern",
                    "pattern": pattern_name,
                    "reason": f"Topic '{conversation_topic}' uses this grammar",
                    "timing": "before_topic",
                    "priority": 0.6,  # Medium priority
                }

            # If weak, review first
            if learner_pattern.mastery_score < 0.6:
                return {
                    "action": "review_pattern",
                    "pattern": pattern_name,
                    "reason": f"Topic '{conversation_topic}' uses this grammar",
                    "timing": "before_topic",
                    "priority": 0.6,  # Medium priority
                }

        # No grammar teaching needed for this topic
        return None

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
            Result dictionary with execution outcomes and generated teaching content:
            {
                "action": str,
                "pattern": str,
                "reasoning": str,
                "teaching_approach": str,
                "executed": bool,
                "teaching_content": Optional[Dict],  # Added for Prompt #2
                "message": str
            }
        """
        action = teaching_plan["action"]
        pattern = teaching_plan.get("pattern")

        result = {
            "action": action,
            "pattern": pattern,
            "reasoning": teaching_plan.get("reasoning", ""),
            "teaching_approach": teaching_plan.get("teaching_approach", "none"),
            "executed": False,
            "teaching_content": None,  # Will be populated by teaching methods
            "message": "",
        }

        if action == "wait":
            result["executed"] = True
            result["message"] = "Continuing conversation flow"
            return result

        if not pattern:
            result["executed"] = False
            result["message"] = f"Action {action} requires a pattern"
            return result

        # Execute the teaching action (methods now return Dict with success/content)
        if action == "introduce_pattern":
            action_result = self._introduce_pattern(pattern, teaching_plan, context)
        elif action == "review_pattern":
            action_result = self._review_pattern(pattern, teaching_plan, context)
        elif action == "reinforce_pattern":
            action_result = self._reinforce_pattern(pattern, teaching_plan, context)
        else:
            action_result = {
                "success": False,
                "teaching_content": None,
                "message": f"Unknown action: {action}"
            }

        # Update result with action results
        result["executed"] = action_result.get("success", False)
        result["teaching_content"] = action_result.get("teaching_content")
        result["message"] = action_result.get("message", result["message"])

        if result["executed"]:
            # Update last grammar teaching turn
            self._last_grammar_teaching_turn = context["conversation"].get("turns_since_last_grammar", 0)

        return result

    def _generate_teaching_content(
        self,
        pattern_name: str,
        teaching_approach: str,
        context: Dict
    ) -> Optional[Dict[str, Any]]:
        """
        Generate teaching content (explanation, examples, practice) for a grammar pattern.

        This is Prompt #2 from the implementation plan. It generates the actual
        teaching material that will be presented to the learner.

        Args:
            pattern_name: Name of the grammar pattern to teach
            teaching_approach: The pedagogical approach (e.g., "explicit_explanation")
            context: Teaching context with learner state and conversation data

        Returns:
            Dict with generated content:
            {
                "strategy": str,
                "explanation": str,
                "examples": List[str],
                "practice_suggestion": str
            }
            Returns None if LLM is not available or generation fails.

        Note: Uses centralized prompts from llm.grammar_prompts for versioning.
        """
        if not self.llm_client:
            print("[GrammarCurriculum] No LLM client available for teaching content generation")
            return None

        # Get pattern details
        curriculum_pattern = self._pattern_map.get(pattern_name)
        if not curriculum_pattern:
            print(f"[GrammarCurriculum] Unknown pattern for content generation: {pattern_name}")
            return None

        try:
            # Get learner's profile for personalization
            learning_style = self.learner_profile.learning_style
            effective_methods = self.learner_profile.effective_teaching_methods or ["explicit_explanation"]

            # Check if learner has struggled with this pattern before
            past_struggles = pattern_name in self.learner_profile.error_prone_patterns

            # Build prompt using centralized template
            system_prompt, user_prompt = build_teaching_approach_prompt(
                pattern_name=pattern_name,
                category=curriculum_pattern.category.value,
                difficulty=str(curriculum_pattern.difficulty_level),  # difficulty_level is int, not Enum
                description=curriculum_pattern.description,
                learning_style=learning_style,
                effective_methods=effective_methods,
                struggles=past_struggles,
                teaching_approach=teaching_approach
            )

            response = self.llm_client.generate_response(
                system_prompt=system_prompt,
                user_message=user_prompt,
                **TEACHING_APPROACH_PARAMS
            )

            # Parse JSON response
            teaching_content = json.loads(response)

            # Validate required fields
            required_fields = ["strategy", "explanation", "examples", "practice_suggestion"]
            for field in required_fields:
                if field not in teaching_content:
                    print(f"[GrammarCurriculum] Missing field in teaching content: {field}")
                    return None

            print(f"[GrammarCurriculum] Generated teaching content for {pattern_name} using {teaching_approach}")
            return teaching_content

        except json.JSONDecodeError as e:
            print(f"[GrammarCurriculum] Failed to parse teaching content JSON: {e}")
            print(f"[GrammarCurriculum] Response was: {response[:200] if 'response' in locals() else 'N/A'}...")
            return None
        except Exception as e:
            import traceback
            print(f"[GrammarCurriculum] Teaching content generation failed: {e}")
            print(f"[GrammarCurriculum] Traceback: {traceback.format_exc()}")
            return None

    def _introduce_pattern(self, pattern_name: str, teaching_plan: Dict, context: Dict) -> Dict[str, Any]:
        """
        Introduce a new grammar pattern.

        Generates teaching content using LLM and creates the pattern record.

        Args:
            pattern_name: Name of pattern to introduce
            teaching_plan: Teaching plan with approach and timing
            context: Teaching context

        Returns:
            Dict with execution status and generated content:
            {
                "success": bool,  # True if pattern was introduced/refreshed
                "teaching_content": Optional[Dict],  # LLM-generated content or None
                "message": str  # Description of what happened
            }
            Where teaching_content (if present) contains:
            {
                "strategy": str,
                "explanation": str,
                "examples": List[str],
                "practice_suggestion": str
            }
        """
        # Check if pattern exists in curriculum
        curriculum_pattern = self._pattern_map.get(pattern_name)
        if not curriculum_pattern:
            return {
                "success": False,
                "teaching_content": None,
                "message": f"Unknown pattern: {pattern_name}"
            }

        # Generate teaching content
        teaching_approach = teaching_plan.get("teaching_approach", "explicit_explanation")
        teaching_content = self._generate_teaching_content(pattern_name, teaching_approach, context)

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

            return {
                "success": True,
                "teaching_content": teaching_content,
                "message": f"Introduced {pattern_name}"
            }

        # Pattern already exists
        return {
            "success": True,
            "teaching_content": teaching_content,
            "message": f"Pattern {pattern_name} already exists, refreshed teaching content"
        }

    def _review_pattern(self, pattern_name: str, teaching_plan: Dict, context: Dict) -> Dict[str, Any]:
        """
        Review an existing grammar pattern.

        Generates focused review content for patterns that need spaced repetition.

        Args:
            pattern_name: Name of pattern to review
            teaching_plan: Teaching plan with approach and timing
            context: Teaching context

        Returns:
            Dict with execution status and generated content:
            {
                "success": bool,  # True if pattern was reviewed successfully
                "teaching_content": Optional[Dict],  # LLM-generated content or None
                "message": str  # Description of what happened
            }
        """
        if pattern_name not in self.learner.grammar_patterns:
            return {
                "success": False,
                "teaching_content": None,
                "message": f"Cannot review unknown pattern: {pattern_name}"
            }

        # Generate teaching content for review
        teaching_approach = teaching_plan.get("teaching_approach", "explicit_explanation")
        teaching_content = self._generate_teaching_content(pattern_name, teaching_approach, context)

        # Record a review attempt (not counted as success/failure yet)
        # The actual learning will be measured in next turns
        print(f"[GrammarCurriculum] Reviewed pattern: {pattern_name}")

        return {
            "success": True,
            "teaching_content": teaching_content,
            "message": f"Reviewed {pattern_name}"
        }

    def _reinforce_pattern(self, pattern_name: str, teaching_plan: Dict, context: Dict) -> Dict[str, Any]:
        """
        Reinforce a weak grammar pattern.

        Generates targeted reinforcement content for patterns the learner struggles with.

        Args:
            pattern_name: Name of pattern to reinforce
            teaching_plan: Teaching plan with approach and timing
            context: Teaching context

        Returns:
            Dict with execution status and generated content:
            {
                "success": bool,  # True if pattern was reinforced successfully
                "teaching_content": Optional[Dict],  # LLM-generated content or None
                "message": str  # Description of what happened
            }
        """
        if pattern_name not in self.learner.grammar_patterns:
            return {
                "success": False,
                "teaching_content": None,
                "message": f"Cannot reinforce unknown pattern: {pattern_name}"
            }

        # Generate teaching content for reinforcement
        # For reinforcement, prefer explicit_explanation approach by default
        teaching_approach = teaching_plan.get("teaching_approach", "explicit_explanation")
        if teaching_approach == "none":
            teaching_approach = "explicit_explanation"  # Override for reinforcement

        teaching_content = self._generate_teaching_content(pattern_name, teaching_approach, context)

        # Record a reinforcement attempt
        print(f"[GrammarCurriculum] Reinforced pattern: {pattern_name}")

        return {
            "success": True,
            "teaching_content": teaching_content,
            "message": f"Reinforced {pattern_name}"
        }

    def _track_teaching_effectiveness(
        self,
        teaching_action: Dict,
        result: Dict,
        current_turn_errors: List[Dict],
        context: Dict
    ) -> None:
        """
        Did our teaching work?

        DESIGN: We evaluate effectiveness in TWO places:
        1. HERE (called at END of turn): Check if previous teaching helped in THIS turn
        2. NEXT TURN: Check if current teaching helps in the FOLLOWING turn

        This bridges the timing gap by:
        - Storing pending teaching action when we teach
        - Evaluating it when we see the next learner input
        - Checking both immediate and next-turn effectiveness

        ⚠️ EFFECTIVENESS MEASUREMENT LIMITATION:
        The underlying `_check_pattern_usage_in_current_turn()` method only checks
        for the absence of errors, not confirmation that the learner actually
        attempted to use the pattern. This means:
        - Success rates may be OVERESTIMATED
        - Strategy effectiveness should be used as one signal among many
        - Not suitable for high-stakes decisions without additional validation
        - See: docs/grammar_curriculum_agent_plan.md Challenge #5

        Args:
            teaching_action: The teaching action we took (dict with pattern, strategy, etc.)
            result: The result of executing the teaching action
            current_turn_errors: Errors that occurred in this turn
            context: Full teaching context for learning style detection
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
                self.teaching_strategy_tracker[previous_strategy] = StrategyStats(
                    strategy_name=previous_strategy
                )

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

            print(f"[GrammarCurriculum] Teaching effectiveness: {previous_strategy} for {previous_pattern} -> {'✓' if success else '✗'}")

        # Step 2: Store CURRENT teaching action for NEXT turn evaluation
        if result.get("action") in ["introduce_pattern", "review_pattern", "reinforce_pattern"]:
            self._pending_teaching_action = {
                "pattern": teaching_action["pattern"],
                "teaching_approach": teaching_action["teaching_approach"],
                "timestamp": datetime.now(),
            }
        else:
            self._pending_teaching_action = None

        # Step 3: Periodically run learning style detection (throttled)
        self._detect_learning_style(context)

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
        - Option 1: Check learner input for grammar category tokens
        - Option 2: Track explicit practice attempts
        - Option 3: Use multi-turn window with decay

        Args:
            pattern_name: Name of the pattern to check
            current_errors: List of errors in current turn

        Returns:
            True if pattern was used correctly (or no errors in category)
        """
        pattern_category = self._get_pattern_category(pattern_name)

        # Check if any errors in this pattern's category
        for error in current_errors:
            if error.get("category") == pattern_category:
                return False  # Error in this category = not successful

        # ⚠️ Simplified check: absence of errors != pattern was used
        # TODO: Implement stricter signal before production
        return True

    def _get_pattern_category(self, pattern_name: str) -> str:
        """
        Get category for a pattern (for grouping related patterns).

        IMPLEMENTATION: Lookup from curriculum definition

        Args:
            pattern_name: Name of the pattern

        Returns:
            Category name as string
        """
        pattern = self._pattern_map.get(pattern_name)
        if pattern:
            return pattern.category.value
        return "general"

    def get_adaptive_curriculum_order(self, learner) -> List[str]:
        """
        Generate personalized curriculum order based on learner needs.

        Algorithm:
        1. Start with base A1 → B1 sequence
        2. Identify learner's weak areas
        3. Move THOSE weak patterns earlier (for reinforcement practice)
        4. Identify learner's strengths
        5. Move DEPENDENT/ADVANCED patterns earlier (accelerate past mastered prerequisites)
        6. Respect prerequisites
        7. Maximize learning efficiency

        KEY DISTINCTION:
        - Weak areas: Move the weak patterns themselves earlier (e.g., basic case patterns from positions 15,25 → 8,18)
        - Strong areas: Move patterns that DEPEND on strengths earlier (e.g., if strong in "basic verbs", move "advanced verb tenses" from position 30 → 20)
        - Result: Weak fundamentals get front-loaded practice; strong fundamentals unlock advanced content faster

        Args:
            learner: The learner object

        Returns:
            List of pattern names in adaptive order
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

    def should_use_adaptive_curriculum(self) -> bool:
        """
        Determine if adaptive curriculum should be used based on learner profile.

        Adaptive curriculum is beneficial when:
        - Learner has identified weaknesses (error-prone patterns)
        - Learner has identified strengths (strength patterns)
        - Enough interaction data has been collected

        Returns:
            True if adaptive curriculum should be used, False otherwise
        """
        # Need sufficient data for adaptive curriculum to be meaningful
        has_weaknesses = len(self.learner_profile.error_prone_patterns) > 0
        has_strengths = len(self.learner_profile.strength_patterns) > 0

        # Check if we have enough interaction data
        total_patterns = len(self.learner.grammar_patterns)
        has_sufficient_data = total_patterns >= 5  # At least 5 patterns attempted

        return has_sufficient_data and (has_weaknesses or has_strengths)

    def get_recommended_next_pattern(self) -> Optional[str]:
        """
        Get the recommended next pattern, automatically choosing between
        static and adaptive curriculum based on learner profile.

        This is the recommended method for getting the next pattern as it
        intelligently decides whether to use adaptive curriculum based on:
        - Amount of learner data collected
        - Presence of identified weaknesses/strengths
        - Learner's current progress

        Returns:
            Name of the next pattern to focus on, or None if all patterns mastered
        """
        use_adaptive = self.should_use_adaptive_curriculum()
        return self.get_next_pattern(use_adaptive=use_adaptive)

    def _reorder_for_reinforcement(
        self,
        order: List[str],
        weaknesses: List[str]
    ) -> List[str]:
        """
        Move the weak patterns THEMSELVES earlier for extra practice.

        EXAMPLE: If learner struggles with "accusative_case" (weakness):
        - Before: accusative_case at position 15
        - After: accusative_case at position 8 (earlier for more practice)

        CONTRAST with _reorder_for_acceleration:
        - Reinforcement: Move the WEAK pattern earlier (the pattern itself)
        - Acceleration: Move DEPENDENT patterns earlier (what comes after strengths)

        If learner struggles with "case", move all case patterns earlier
        and add more spacing between them for practice.

        IMPLEMENTATION: Rule-based category prioritization

        ALGORITHM:
        1. Extract categories from weaknesses (e.g., "accusative_case" → "case")
        2. Find all patterns in weak categories
        3. Group them by category
        4. Move each weak category earlier in sequence
        5. Insert review patterns between weak category patterns

        Args:
            order: Current curriculum order
            weaknesses: List of pattern names the learner struggles with

        Returns:
            Reordered list with weak patterns moved earlier
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

    def _reorder_for_acceleration(
        self,
        order: List[str],
        strengths: List[str]
    ) -> List[str]:
        """
        Move DEPENDENT patterns earlier when learner has strong fundamentals.

        EXAMPLE: If learner is strong in "present_tense_regular" (strength):
        - Before: perfect_tense at position 15 (requires present_tense_regular at position 2)
        - After: perfect_tense at position 8 (accelerated because prerequisite is mastered)

        CONTRAST with _reorder_for_reinforcement:
        - Reinforcement: Move the WEAK pattern earlier (the pattern itself)
        - Acceleration: Move DEPENDENT patterns earlier (what comes after strengths)

        IMPLEMENTATION: Check prerequisite satisfaction

        ALGORITHM:
        1. For each strength, find what patterns it enables (via PATTERN_DEPENDENCIES)
        2. Check if those enabled patterns can be moved earlier
        3. Move them earlier if their prerequisites are met
        4. Preserve relative order among accelerated patterns

        Args:
            order: Current curriculum order
            strengths: List of pattern names the learner is strong in

        Returns:
            Reordered list with dependent patterns moved earlier
        """
        if not strengths:
            return order

        # Step 1: Find patterns that can be accelerated
        # (their prerequisites are all in strengths)
        accelerated_patterns = []
        other_patterns = []

        for pattern_name in order:
            # Skip if already in strengths (we're looking for dependent patterns)
            if pattern_name in strengths:
                other_patterns.append(pattern_name)
                continue

            # Check if this pattern's prerequisites are all mastered
            dependency = self.PATTERN_DEPENDENCIES.get(pattern_name)
            if not dependency or not dependency.requires:
                # No dependencies or not in our dependency graph
                other_patterns.append(pattern_name)
                continue

            # Check if all prerequisites are in strengths
            prerequisites_met = all(
                prereq in strengths for prereq in dependency.requires
            )

            if prerequisites_met:
                # This pattern can be accelerated!
                accelerated_patterns.append(pattern_name)
            else:
                other_patterns.append(pattern_name)

        # Step 2: Build new order with accelerated patterns moved earlier
        # Insert accelerated patterns after their prerequisites but before they would normally appear
        new_order = []
        accelerated_inserted = set()

        for pattern_name in order:
            # Add pattern to new order
            if pattern_name in other_patterns and pattern_name not in accelerated_inserted:
                new_order.append(pattern_name)

            # Check if we should insert any accelerated patterns here
            # (after their prerequisites)
            for accelerated_pattern in accelerated_patterns:
                if accelerated_pattern in accelerated_inserted:
                    continue

                dependency = self.PATTERN_DEPENDENCIES.get(accelerated_pattern)
                if dependency and dependency.requires:
                    # Check if all prerequisites have been added
                    if all(prereq in new_order for prereq in dependency.requires):
                        # Insert this accelerated pattern here
                        new_order.append(accelerated_pattern)
                        accelerated_inserted.add(accelerated_pattern)

        # Add any remaining accelerated patterns that weren't inserted
        for pattern_name in accelerated_patterns:
            if pattern_name not in accelerated_inserted:
                new_order.append(pattern_name)

        return new_order

    def _validate_dependencies(self, order: List[str]) -> List[str]:
        """
        Validate that prerequisites are satisfied in the given order.

        Ensures that for every pattern in the order, all its prerequisites
        appear before it.

        IMPLEMENTATION: Dependency validation with circular dependency detection

        ALGORITHM:
        1. Track which patterns have been seen
        2. For each pattern, check if its prerequisites are in the seen set
        3. If not, move the pattern after its prerequisites
        4. Detect and handle circular dependencies gracefully
        5. Return validated order

        Args:
            order: Proposed curriculum order

        Returns:
            Validated order with all prerequisites satisfied
        """
        validated_order = []
        seen_patterns = set()
        unresolved_patterns = set(order)

        # May need multiple passes to resolve all dependencies
        max_iterations = len(order) * 2  # Prevent infinite loops
        iteration = 0
        stuck_count = 0  # Track how many iterations we've made no progress
        last_validated_count = 0

        while len(validated_order) < len(order) and iteration < max_iterations:
            iteration += 1
            progress_made = False
            stuck_patterns = []  # Track patterns that couldn't be resolved this pass

            for pattern_name in order:
                if pattern_name in validated_order:
                    continue

                # Check if this pattern has dependencies
                dependency = self.PATTERN_DEPENDENCIES.get(pattern_name)

                if not dependency or not dependency.requires:
                    # No dependencies, can add immediately
                    validated_order.append(pattern_name)
                    seen_patterns.add(pattern_name)
                    unresolved_patterns.discard(pattern_name)
                    progress_made = True
                else:
                    # Check if all prerequisites are satisfied
                    missing_prereqs = [
                        prereq for prereq in dependency.requires
                        if prereq not in seen_patterns
                    ]

                    if not missing_prereqs:
                        # All prerequisites met
                        validated_order.append(pattern_name)
                        seen_patterns.add(pattern_name)
                        unresolved_patterns.discard(pattern_name)
                        progress_made = True
                    else:
                        # Track this pattern as stuck for now
                        stuck_patterns.append((pattern_name, missing_prereqs))

            # Check for circular dependency or missing prerequisite patterns
            if len(validated_order) == last_validated_count:
                stuck_count += 1
                if stuck_count >= 2:
                    # We've been stuck for 2 iterations - this indicates a problem
                    print(f"[GrammarCurriculum] Dependency validation stuck at iteration {iteration}")
                    print(f"[GrammarCurriculum] Unresolved patterns: {unresolved_patterns}")

                    # Analyze stuck patterns for circular dependencies
                    for pattern_name, missing_prereqs in stuck_patterns:
                        # Check if missing prereqs are also stuck (potential circular dependency)
                        circular_candidates = [p for p in missing_prereqs if p in unresolved_patterns]
                        if circular_candidates:
                            print(f"[GrammarCurriculum] Potential circular dependency: "
                                  f"'{pattern_name}' depends on {circular_candidates} "
                                  f"which are also unresolved")

                    # Add remaining patterns in their original order with a warning
                    print("[GrammarCurriculum] Adding remaining patterns without dependency resolution")
                    for pattern_name in order:
                        if pattern_name not in validated_order:
                            validated_order.append(pattern_name)
                            seen_patterns.add(pattern_name)
                    break
            else:
                stuck_count = 0  # Reset stuck counter if we made progress

            last_validated_count = len(validated_order)

        if iteration >= max_iterations:
            print(f"[GrammarCurriculum] Warning: Dependency validation reached max iterations ({max_iterations})")

        return validated_order

    def _detect_learning_style(self, context: Dict) -> None:
        """
        Detect learner's grammar learning style using LLM analysis.

        This method is throttled to run every 50 turns to avoid excessive LLM calls.
        When triggered, it analyzes recent learner interactions to determine:
        - Learning style (analytical, visual, immersion)
        - Effective teaching methods
        - Patterns they struggle with
        - Patterns they excel at

        Args:
            context: Teaching context with learner state and conversation data

        Note: Uses centralized prompts from llm.grammar_prompts for versioning.
        """
        # Increment counter
        self._learning_style_detection_turns += 1

        # Check if we should run detection (throttled)
        if self._learning_style_detection_turns < self._learning_style_detection_interval:
            return

        # Reset counter
        self._learning_style_detection_turns = 0

        # Check if LLM client is available
        if not self.llm_client:
            print("[GrammarCurriculum] No LLM client available for learning style detection")
            return

        print("[GrammarCurriculum] Running learning style detection...")

        try:
            # Build prompt for learning style detection
            learner_state = context["learner_state"]
            recent_errors = learner_state["recent_errors"]
            mastered_patterns = list(learner_state["mastered_patterns"].keys())

            # Collect strategy effectiveness data
            strategy_effectiveness = []
            for strategy_name, stats in self.teaching_strategy_tracker.items():
                if stats.attempts > 0:
                    strategy_effectiveness.append(
                        f"{strategy_name}: {stats.success_rate:.1%} success rate ({stats.attempts} attempts)"
                    )

            # Build prompt using centralized template
            system_prompt, user_prompt = build_learner_profiling_prompt(
                recent_errors=recent_errors,
                mastered_patterns=mastered_patterns,
                strategy_effectiveness=strategy_effectiveness,
                current_profile=self.learner_profile.learning_style
            )

            response = self.llm_client.generate_response(
                system_prompt=system_prompt,
                user_message=user_prompt,
                **LEARNER_PROFILING_PARAMS
            )

            # Parse JSON response
            detection_result = json.loads(response)

            # Update learner profile with detected learning style
            if "learning_style" in detection_result:
                self.learner_profile.update_learning_style(detection_result["learning_style"])
                print(f"[GrammarCurriculum] Detected learning style: {detection_result['learning_style']}")

            # Update effective methods if provided
            if "effective_methods" in detection_result:
                for method in detection_result["effective_methods"]:
                    if method not in self.learner_profile.effective_teaching_methods:
                        self.learner_profile.effective_teaching_methods.append(method)

            # Update struggle patterns if provided
            if "struggle_patterns" in detection_result:
                for pattern in detection_result["struggle_patterns"]:
                    if pattern not in self.learner_profile.error_prone_patterns:
                        self.learner_profile.error_prone_patterns.append(pattern)

            # Update strength patterns if provided
            if "strength_patterns" in detection_result:
                for pattern in detection_result["strength_patterns"]:
                    if pattern not in self.learner_profile.strength_patterns:
                        self.learner_profile.strength_patterns.append(pattern)

            # Update optimal teaching frequency if provided
            if "optimal_frequency" in detection_result:
                self.learner_profile.optimal_teaching_frequency = detection_result["optimal_frequency"]
                print(f"[GrammarCurriculum] Detected optimal teaching frequency: {detection_result['optimal_frequency']}")

            print("[GrammarCurriculum] Learning style detection completed successfully")

        except json.JSONDecodeError as e:
            print(f"[GrammarCurriculum] Learning style detection failed (JSON parsing): {e}")
            # Don't update profile on failure - keep existing data
        except Exception as e:
            import traceback
            print(f"[GrammarCurriculum] Learning style detection failed: {e}")
            print(f"[GrammarCurriculum] Traceback: {traceback.format_exc()}")
            # Don't update profile on failure - keep existing data

    def get_capabilities(self) -> List[str]:
        """Return what this agent can do."""
        return [
            "manage structured grammar curriculum (A1 -> B1)",
            "route grammar errors to correct pattern with metadata",
            "track learner progress through curriculum",
            "determine readiness to advance to next pattern",
            "suggest next focus pattern based on mastery",
            # Phase 2: Learning & Adaptation capabilities
            "learn which teaching strategies work for individual learners",
            "track teaching effectiveness over time",
            "adapt teaching approach based on learner profile",
            "detect learner's grammar learning style (analytical/visual/immersion)",
            "remember teaching insights across sessions (persistence)",
            # Phase 3: Proactive Teaching capabilities
            "teach grammar before errors occur (predictive teaching)",
            "generate personalized curriculum order based on learner needs",
            "reinforce weak patterns by moving them earlier in curriculum",
            "accelerate learning by introducing advanced patterns when prerequisites mastered",
            "respect pattern dependencies and prerequisites",
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

        # Step 5: REFLECT - Track effectiveness and learn from results
        self._track_teaching_effectiveness(
            teaching_action=teaching_plan,  # The action we took
            result=result,                   # The result of executing it
            current_turn_errors=errors,      # Errors in this turn
            context=context                  # Full context for learning style detection
        )

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

    def get_next_pattern(self, use_adaptive: bool = False) -> Optional[str]:
        """
        Get the next pattern the learner should focus on.

        Returns the next GrammarPattern from the curriculum that the learner
        has not yet mastered, respecting the learner's current CEFR level.

        Args:
            use_adaptive: If True, use personalized adaptive curriculum order.
                        If False (default), use standard sequential curriculum.
                        Adaptive curriculum requires learner profile data from Phase 2.

        Returns:
            Name of the next pattern to focus on, or None if all appropriate patterns mastered
        """
        # Choose curriculum order based on parameter
        if use_adaptive:
            # Use adaptive curriculum (Phase 3: Proactive Teaching)
            # This requires learner profile with weaknesses/strengths from Phase 2
            if self.learner_profile.error_prone_patterns or self.learner_profile.strength_patterns:
                curriculum_order = self.get_adaptive_curriculum_order(self.learner)
                print(f"[GrammarCurriculum] Using adaptive curriculum order (reordered based on learner profile)")
            else:
                # Fall back to static curriculum if no profile data yet
                curriculum_order = [p.name for p in self.GERMAN_GRAMMAR_CURRICULUM]
                print(f"[GrammarCurriculum] No learner profile data yet, using static curriculum")
        else:
            # Use standard sequential curriculum (original behavior)
            curriculum_order = [p.name for p in self.GERMAN_GRAMMAR_CURRICULUM]

        # Filter by learner's CEFR level
        learner_level = self.learner.current_cefr_level
        level_order = ["A1", "A2", "B1"]
        accessible_levels = set()

        for level in level_order:
            accessible_levels.add(level)
            if level == learner_level:
                break

        # Search through curriculum order for next unmastered pattern
        for pattern_name in curriculum_order:
            # Check if pattern is accessible at learner's level
            pattern = self._pattern_map.get(pattern_name)
            if not pattern:
                continue

            if pattern.introduced_at_level not in accessible_levels:
                continue

            # Check if learner has mastered this pattern
            learner_pattern = self.learner.grammar_patterns.get(pattern_name)

            # If pattern doesn't exist or isn't mastered, it's a candidate
            if learner_pattern is None:
                return pattern_name

            if learner_pattern.mastery_score < 0.7:
                return pattern_name

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
