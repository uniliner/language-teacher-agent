"""
Pronunciation teaching agent for teaching pronunciation patterns.

This agent specializes in teaching pronunciation by:
- Selecting appropriate patterns to teach based on learner state
- Using the LLM to generate personalized explanations
- Tracking progress with spaced repetition
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import Agent, AgentConfig
from models.pronunciation import PronunciationPattern, PronunciationCategory
from models.learner import Learner
from llm.client import LLMClient


class PronunciationTeachingAgent(Agent):
    """
    Agent for teaching pronunciation patterns.

    This agent implements the teaching-focused agent pattern:
    1. Selects what to teach (pattern selection)
    2. Generates teaching content (LLM integration)
    3. Tracks learner progress (state updates)
    """

    def __init__(
        self,
        config: AgentConfig,
        learner: Learner,
        llm_client: Optional[LLMClient] = None,
        patterns_file: Optional[str] = None,
    ):
        """
        Initialize the pronunciation teaching agent.

        Args:
            config: Agent configuration
            learner: Learner state
            llm_client: LLM client for generating content
            patterns_file: Path to pronunciation patterns JSON file
        """
        super().__init__(config, learner, llm_client)

        # Load pronunciation patterns database
        self.patterns_file = patterns_file or self._find_patterns_file()
        self.patterns_database = self._load_patterns()

    def _find_patterns_file(self) -> str:
        """Find the pronunciation patterns JSON file."""
        # Try multiple possible locations (prioritize src/data to avoid confusion with learner files)
        possible_paths = [
            "src/data/pronunciation_patterns.json",
            "data/pronunciation_patterns.json",
            "../data/pronunciation_patterns.json",
        ]

        for path in possible_paths:
            if Path(path).exists():
                return path

        # Default to src/data/pronunciation_patterns.json
        return "src/data/pronunciation_patterns.json"

    def _load_patterns(self) -> Dict[str, PronunciationPattern]:
        """
        Load pronunciation patterns from JSON file.

        Returns:
            Dictionary mapping pattern_id to PronunciationPattern
        """
        try:
            with open(self.patterns_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            patterns = {}
            for pattern_data in data.get("patterns", []):
                pattern = PronunciationPattern(**pattern_data)
                patterns[pattern.pattern_id] = pattern

            return patterns
        except FileNotFoundError:
            print(f"Warning: Pronunciation patterns file not found at {self.patterns_file}")
            return {}
        except json.JSONDecodeError as e:
            print(f"Error parsing pronunciation patterns: {e}")
            return {}

    def get_capabilities(self) -> list[str]:
        """Return what this agent can do."""
        return [
            "teach pronunciation patterns",
            "demonstrate sound production",
            "identify common pronunciation mistakes",
            "track pronunciation progress with spaced repetition",
            "provide personalized pronunciation feedback",
        ]

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process input and generate pronunciation teaching response.

        This is the main agent method that orchestrates:
        1. Pattern selection (what to teach?)
        2. Content generation (how to teach it?)
        3. State updates (track progress)

        Args:
            input_data: Dictionary containing:
                - learner: Learner state
                - conversation_state: Current conversation context
                - recent_words: Optional list of recently encountered words
                - decision: Optional TeachingDecision object

        Returns:
            Dictionary with:
                - explanation: Teaching explanation
                - practice_word: Word to practice
                - pattern_id: ID of pattern taught
                - teaching_action: What was done
                - updated_state: Changes to learner state
        """
        learner = input_data.get("learner", self.learner)
        conversation_state = input_data.get("conversation_state", {})
        recent_words = input_data.get("recent_words", [])

        # Step 1: Select pattern to teach
        pattern = self._select_pattern(learner, conversation_state, recent_words)

        if not pattern:
            # No appropriate pattern found
            return {
                "explanation": None,
                "practice_word": None,
                "pattern_id": None,
                "teaching_action": "skip",
                "reason": "No appropriate pattern found for teaching",
                "updated_state": {},
            }

        # Step 2: Generate teaching content
        teaching_content = self._generate_teaching_content(
            pattern=pattern,
            learner=learner,
            conversation_state=conversation_state,
        )

        # Step 3: Update learner progress
        updated_state = self._update_learner_progress(learner, pattern, teaching_content)

        return {
            **teaching_content,
            "updated_state": updated_state,
            "teaching_action": "teach_pronunciation",
        }

    def _select_pattern(
        self,
        learner: Learner,
        conversation_state: Dict[str, Any],
        recent_words: List[str],
    ) -> Optional[PronunciationPattern]:
        """
        Select which pattern to teach.

        Priority order:
        1. Patterns due for review (spaced repetition)
        2. Patterns relevant to recently encountered words
        3. New patterns based on learner's CEFR level

        Args:
            learner: Current learner state
            conversation_state: Conversation context
            recent_words: Recently encountered words

        Returns:
            Selected PronunciationPattern or None
        """
        # Get learner's pronunciation patterns (if any)
        learner_patterns = learner.pronunciation_patterns if hasattr(learner, "pronunciation_patterns") else {}

        # Priority 1: Check for patterns due for review
        now = datetime.now()
        for pattern_id, pattern in learner_patterns.items():
            if pattern.is_due_for_review and pattern.mastery_score < 0.8:
                # Found a pattern that needs review
                return self.patterns_database.get(pattern_id)

        # Priority 2: Check for patterns in recently encountered words
        if recent_words:
            for word in recent_words[:5]:  # Check last 5 words
                for pattern_id, pattern in self.patterns_database.items():
                    # If word contains this pattern and learner hasn't mastered it
                    if word.lower() in [e.lower() for e in pattern.examples]:
                        learner_pattern = learner_patterns.get(pattern_id)
                        if not learner_pattern or learner_pattern.mastery_score < 0.6:
                            return pattern

        # Priority 3: Select a new pattern based on CEFR level
        return self._select_new_pattern(learner, learner_patterns)

    def _select_new_pattern(
        self,
        learner: Learner,
        learner_patterns: Dict[str, PronunciationPattern],
    ) -> Optional[PronunciationPattern]:
        """
        Select a new pattern the learner hasn't encountered yet.

        Args:
            learner: Current learner state
            learner_patterns: Patterns learner has already seen

        Returns:
            New PronunciationPattern or None
        """
        cefr_level = learner.current_cefr_level

        # Get patterns matching learner's level
        candidate_patterns = []
        for pattern in self.patterns_database.values():
            # Skip if already encountered
            if pattern.pattern_id in learner_patterns:
                continue

            # Check if pattern difficulty matches learner's level
            if self._is_pattern_appropriate(pattern.difficulty, cefr_level):
                candidate_patterns.append(pattern)

        if not candidate_patterns:
            return None

        # Sort by difficulty and return first
        candidate_patterns.sort(key=lambda p: p.difficulty)
        return candidate_patterns[0]

    def _is_pattern_appropriate(self, pattern_difficulty: str, learner_level: str) -> bool:
        """
        Check if a pattern is appropriate for learner's level.

        Args:
            pattern_difficulty: Pattern difficulty (A1, A2, B1, etc.)
            learner_level: Learner's CEFR level

        Returns:
            True if pattern is appropriate
        """
        level_order = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}

        pattern_level = level_order.get(pattern_difficulty, 2)
        learner_level_num = level_order.get(learner_level, 1)

        # Pattern should be at or slightly above learner's level
        # But not too far ahead (max 1 level above)
        return pattern_level <= learner_level_num + 1

    def _generate_teaching_content(
        self,
        pattern: PronunciationPattern,
        learner: Learner,
        conversation_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate personalized teaching content using LLM.

        Args:
            pattern: Pattern to teach
            learner: Learner state
            conversation_state: Conversation context

        Returns:
            Dictionary with teaching content
        """
        if not self.llm_client:
            # Fallback to static content
            return {
                "explanation": f"{pattern.description}. {pattern.teaching_notes}",
                "practice_word": pattern.examples[0] if pattern.examples else "",
                "pattern_id": pattern.pattern_id,
                "pattern_name": pattern.name,
            }

        # Build prompt for LLM
        prompt = self._build_teaching_prompt(pattern, learner, conversation_state)

        try:
            response = self.llm_client.generate_response(
                system_prompt=self._get_system_prompt(),
                user_message=prompt,
                temperature=0.7,
                max_tokens=400,
            )

            return {
                "explanation": response,
                "practice_word": pattern.examples[0] if pattern.examples else "",
                "pattern_id": pattern.pattern_id,
                "pattern_name": pattern.name,
                "all_examples": pattern.examples,
            }
        except Exception as e:
            print(f"Error generating pronunciation content: {e}")
            # Fallback
            return {
                "explanation": f"{pattern.description}. {pattern.teaching_notes}",
                "practice_word": pattern.examples[0] if pattern.examples else "",
                "pattern_id": pattern.pattern_id,
                "pattern_name": pattern.name,
            }

    def _build_teaching_prompt(
        self,
        pattern: PronunciationPattern,
        learner: Learner,
        conversation_state: Dict[str, Any],
    ) -> str:
        """Build prompt for LLM to generate teaching content."""
        examples_str = ", ".join(pattern.examples[:3])
        mistakes_str = "\n".join(f"- {m}" for m in pattern.common_mistakes[:2])

        prompt = f"""Teach this German pronunciation pattern to an {learner.current_cefr_level} learner:

Pattern: {pattern.name}
Description: {pattern.description}
Examples: {examples_str}

Teaching Notes: {pattern.teaching_notes}

Common Mistakes to Address:
{mistakes_str}

Generate a brief, friendly explanation (2-3 sentences) that helps the learner pronounce this correctly.
Then suggest they try saying: {pattern.examples[0]}

Keep it encouraging and practical!"""

        return prompt

    def _get_system_prompt(self) -> str:
        """Get system prompt for pronunciation teaching."""
        return """You are a friendly German pronunciation teacher helping learners improve their accent.

Your teaching style:
- Encouraging and supportive
- Focus on one key technique at a time
- Use simple, concrete instructions
- Provide actionable tips they can use immediately
- Keep explanations brief (2-3 sentences)
- End with a practice suggestion

Remember: The goal is to help them sound more natural, not perfect. Every small improvement counts!"""

    def _update_learner_progress(
        self,
        learner: Learner,
        pattern: PronunciationPattern,
        teaching_content: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update learner state with pronunciation progress.

        Args:
            learner: Learner to update
            pattern: Pattern being taught
            teaching_content: Content that was taught

        Returns:
            Dictionary of state changes
        """
        # Ensure learner has pronunciation_patterns dict
        if not hasattr(learner, "pronunciation_patterns"):
            learner.pronunciation_patterns = {}

        # Get or create pattern in learner's state
        if pattern.pattern_id not in learner.pronunciation_patterns:
            # Create new pattern instance for learner
            learner.pronunciation_patterns[pattern.pattern_id] = PronunciationPattern(
                pattern_id=pattern.pattern_id,
                name=pattern.name,
                category=pattern.category,
                difficulty=pattern.difficulty,
                description=pattern.description,
                examples=pattern.examples,
                teaching_notes=pattern.teaching_notes,
                common_mistakes=pattern.common_mistakes,
                ipa_symbol=pattern.ipa_symbol,
                sound_description=pattern.sound_description,
            )

        # Record that this pattern was encountered
        learner_pattern = learner.pronunciation_patterns[pattern.pattern_id]
        practice_word = teaching_content.get("practice_word", "")
        if practice_word:
            learner_pattern.encounter_in_word(practice_word)

        # Update timestamp
        learner.last_updated = datetime.now()

        return {
            "pattern_encountered": pattern.pattern_id,
            "practice_word": practice_word,
        }

    def get_all_patterns(self) -> List[PronunciationPattern]:
        """Get all available pronunciation patterns."""
        return list(self.patterns_database.values())

    def get_pattern_by_id(self, pattern_id: str) -> Optional[PronunciationPattern]:
        """Get a specific pattern by ID."""
        return self.patterns_database.get(pattern_id)

    def get_patterns_by_category(self, category: PronunciationCategory) -> List[PronunciationPattern]:
        """Get all patterns in a specific category."""
        return [p for p in self.patterns_database.values() if p.category == category]
