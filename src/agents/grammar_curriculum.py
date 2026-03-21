"""
Grammar curriculum agent for progressive grammar instruction.

This agent manages a structured curriculum of grammar patterns for German
learners, tracking which patterns have been introduced and determining when
the learner is ready to advance to more complex patterns.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from .base import Agent, AgentConfig
from models.grammar import GrammarWeakness


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
            llm_client: LLM client (not used by this agent but required by base)
        """
        super().__init__(config, learner, llm_client)

        # Build lookup maps for efficient pattern finding
        self._pattern_map = {p.name: p for p in self.GERMAN_GRAMMAR_CURRICULUM}
        self._patterns_by_level = self._build_level_index()
        self._patterns_by_category = self._build_category_index()

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
        Process grammar errors and update learner state.

        Takes detected errors from analyze_learner_input and routes them to
        the correct GrammarPattern on the Learner object.

        Args:
            input_data: Dictionary containing:
                - errors: List of error dicts from analyze_learner_input
                - learner_input: What the learner said (optional)

        Returns:
            Dictionary with:
                - patterns_updated: List of pattern names that were updated
                - ready_to_advance: bool indicating if learner can advance
                - suggested_focus: Next pattern to focus on (if any)
                - current_position: Current position in curriculum
        """
        errors = input_data.get("errors", [])
        learner_input = input_data.get("learner_input", "")

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

        # Determine if learner is ready to advance
        ready_to_advance = self.is_ready_to_advance()

        # Get next suggested focus
        suggested_focus = self.get_next_pattern()

        # Get current position in curriculum
        current_position = self._get_current_position()

        return {
            "patterns_updated": patterns_updated,
            "ready_to_advance": ready_to_advance,
            "suggested_focus": suggested_focus,
            "current_position": current_position,
        }

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
