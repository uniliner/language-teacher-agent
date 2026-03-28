"""
Conversation agent for natural language practice.

This agent conducts conversations in the target language while
tracking learner progress and making pedagogical decisions.
"""

from typing import Any, Dict, List, Optional

from .base import Agent, AgentConfig
from .grammar_curriculum import GrammarCurriculumAgent
from models.learner import Learner, ConfidenceLevel
from pedagogy.engine import PedagogicalEngine, TeachingDecision
from llm.client import LLMClient, Message


class ConversationAgent(Agent):
    """
    Agent for conducting adaptive conversations.

    This is the primary agent that:
    - Converses naturally in the target language
    - Analyzes learner input for errors
    - Makes pedagogical decisions (correct, introduce, review)
    - Tracks vocabulary and grammar progress
    - Adjusts to learner confidence level
    """

    def __init__(
        self,
        config: AgentConfig,
        learner: Learner,
        llm_client: LLMClient,
        pedagogical_engine: Optional[PedagogicalEngine] = None,
        grammar_curriculum_agent: Optional[GrammarCurriculumAgent] = None,
        experimentation_mode: bool = False,
    ):
        super().__init__(config, learner, llm_client)

        # Pedagogical engine for decision making
        self.pedagogical_engine = pedagogical_engine or PedagogicalEngine(
            learner, experimentation_mode=experimentation_mode
        )
        self.experimentation_mode = experimentation_mode

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

        # Conversation state
        self.conversation_active = False
        self.current_topic: Optional[str] = None
        self.turns_in_session = 0

    def get_capabilities(self) -> list[str]:
        """Return what this agent can do."""
        return [
            "natural conversation in target language",
            "error detection and correction",
            "vocabulary tracking and spaced repetition",
            "grammar pattern recognition",
            "adaptive difficulty adjustment",
            "confidence monitoring",
        ]

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process learner input and generate response.

        Args:
            input_data: Dictionary containing:
                - learner_input: What the learner said
                - conversation_context: Current conversation state

        Returns:
            Dictionary with:
                - response: Agent's response
                - errors: Errors detected (if any)
                - teaching_action: What pedagogical action was taken
                - updated_state: Changes to learner state
        """
        learner_input = input_data.get("learner_input", "")
        conversation_context = input_data.get("conversation_context", {})

        # Step 1: Analyze learner input
        analysis = self._analyze_input(learner_input)

        # Step 2: Make pedagogical decision
        decision = self.pedagogical_engine.analyze_turn(
            learner_input=learner_input,
            detected_errors=analysis.get("errors", []),
            conversation_state=conversation_context,
        )

        # Step 3: Generate response based on decision
        response = self._generate_response(learner_input, decision, analysis)

        # Step 4: Update learner state
        updated_state = self._update_learner_from_interaction(
            learner_input, analysis, decision
        )

        # Step 5: Update conversation history
        self._add_to_conversation_history(learner_input, response, analysis)

        return {
            "response": response,
            "errors": analysis.get("errors", []),
            "teaching_decision": str(decision),
            "teaching_action": decision.action,
            "updated_state": updated_state,
            "metadata": {
                "agent": self.config.name,
                "turn": self.turns_in_session,
                "strategy": str(decision.strategy) if decision.strategy else None,
            },
        }

    def _analyze_input(self, learner_input: str) -> Dict[str, Any]:
        """Analyze learner input for errors and vocabulary."""
        if not self.llm_client:
            return {"errors": [], "vocabulary_used": []}

        try:
            # Get valid pattern names from the curriculum agent
            valid_patterns = GrammarCurriculumAgent.get_valid_pattern_names()

            # Get recent learner inputs for recurring error detection
            recent_inputs = [
                turn.get("learner_input", "")
                for turn in self.learner.recent_conversations[-5:]
                if turn.get("learner_input")
            ]

            analysis = self.llm_client.analyze_learner_input(
                learner_input=learner_input,
                target_language=self.config.target_language,
                learner_level=self.learner.current_cefr_level,
                valid_grammar_patterns=valid_patterns,
                recent_learner_inputs=recent_inputs,
            )
            return analysis
        except Exception as e:
            # Fallback if analysis fails
            print(f"Warning: Analysis failed ({e}), continuing without detailed analysis")
            return {"errors": [], "vocabulary_used": [], "intended_meaning": learner_input}

    def _generate_response(
        self,
        learner_input: str,
        decision: TeachingDecision,
        analysis: Dict[str, Any],
    ) -> str:
        """Generate appropriate response based on decision."""

        if not self.llm_client:
            # Fallback response
            return f"I understand: {learner_input}. Let's continue!"

        try:
            conversation_context = {
                "confidence": self.learner.confidence,
                "error_rate": self.pedagogical_engine.error_count
                / max(self.pedagogical_engine.turn_count, 1),
                "cefr_level": self.learner.current_cefr_level,
                "topic": self.current_topic,
            }

            response = self.llm_client.generate_teaching_response(
                learner_input=learner_input,
                decision=decision,
                conversation_context=conversation_context,
                target_language=self.config.target_language,
            )

            return response
        except Exception as e:
            print(f"Error generating response: {e}")
            return "Es tut mir leid, could you please repeat that?"

    def _update_learner_from_interaction(
        self,
        learner_input: str,
        analysis: Dict[str, Any],
        decision: TeachingDecision,
    ) -> Dict[str, Any]:
        """Update learner state based on the interaction."""
        updates = {}

        # Track vocabulary used
        vocabulary_data = analysis.get("vocabulary_used", [])
        for vocab_item_data in vocabulary_data:
            # Handle both old format (string) and new format (dict)
            if isinstance(vocab_item_data, str):
                # Old format - just the word
                word = vocab_item_data
                translation = ""
                part_of_speech = "unknown"
            else:
                # New format - dict with word, translation, part_of_speech
                word = vocab_item_data.get("word", "")
                translation = vocab_item_data.get("translation", "")
                part_of_speech = vocab_item_data.get("part_of_speech", "unknown")

            if not word:
                continue

            vocab_item = self.learner.get_vocabulary(word)
            if vocab_item:
                vocab_item.record_encounter(context=learner_input[:50])
            elif translation:  # Only create new words if we have translation
                self.learner.add_or_update_vocabulary(
                    word=word,
                    translation=translation,
                    part_of_speech=part_of_speech,
                    context=learner_input[:50],
                )

        # Use GrammarCurriculumAgent for grammar tracking
        grammar_result = self.grammar_curriculum_agent.process(
            input_data={
                "errors": analysis.get("errors", []),
                "learner_input": learner_input,
            }
        )

        # Track grammar updates in response
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

    def _add_to_conversation_history(
        self,
        learner_input: str,
        agent_response: str,
        analysis: Dict[str, Any],
    ) -> None:
        """Add conversation to learner's history."""

        turn_record = {
            "turn": self.turns_in_session,
            "timestamp": self.learner.last_updated.isoformat(),
            "learner_input": learner_input,
            "agent_response": agent_response,
            "errors_count": len(analysis.get("errors", [])),
            "teaching_action": getattr(
                self.pedagogical_engine,
                "current_mode",
                "conversation",
            ),
        }

        # Add to recent conversations (keep last 50)
        self.learner.recent_conversations.append(turn_record)
        if len(self.learner.recent_conversations) > 50:
            self.learner.recent_conversations = self.learner.recent_conversations[-50:]

    def start_conversation(self, topic: Optional[str] = None) -> str:
        """
        Start a new conversation session.

        Args:
            topic: Optional topic to focus on

        Returns:
            Opening message
        """
        self.conversation_active = True
        self.current_topic = topic
        self.turns_in_session = 0
        self.pedagogical_engine = PedagogicalEngine(
            self.learner, experimentation_mode=self.experimentation_mode
        )  # Reset engine

        # Generate opening
        if topic:
            opening = f"Hallo! Let's talk about {topic} today. How are you?"
        else:
            opening = "Hallo! How are you today? What would you like to talk about?"

        # Translate to German with context
        if self.llm_client:
            try:
                opening_prompt = f"""Generate exactly ONE short opening message for a {self.config.target_language} conversation practice session.
Learner level: {self.learner.current_cefr_level}
Topic: {topic or 'general conversation'}

IMPORTANT CONSTRAINTS:
- Return ONLY a single opening message in {self.config.target_language}
- Do NOT provide multiple options
- Do NOT use numbering or bullet points
- Do NOT use markdown headers (like ## or ###)
- Do NOT include any meta-commentary or explanations
- Just output the greeting itself, nothing else

Keep it simple, friendly, and welcoming."""

                opening = self.llm_client.generate_response(
                    system_prompt=f"You are a friendly {self.config.target_language} language teacher. You always respond with exactly one message, never multiple options.",
                    user_message=opening_prompt,
                    temperature=0.8,
                    max_tokens=100,
                )

                # Cleanup: if LLM still returned multiple options, extract the first one
                opening = self._extract_single_opening(opening)
            except Exception:
                pass  # Use fallback

        return opening

    def _extract_single_opening(self, text: str) -> str:
        """Extract a single opening message from text that might contain multiple options."""
        lines = text.strip().split('\n')
        first_line = lines[0].strip()

        # Remove common prefixes
        for prefix in ["1.", "2.", "3.", "-", "•", "*", "Option", "Here", "Here's"]:
            if first_line.startswith(prefix):
                first_line = first_line[len(prefix):].strip()

        # Remove markdown headers
        first_line = first_line.lstrip('#').strip()

        # Remove meta-commentary prefixes
        if first_line.lower().startswith(("here is", "here's", "you could say", "you might say")):
            # Try to find the actual quote
            if '"' in first_line:
                parts = first_line.split('"')
                if len(parts) >= 2:
                    first_line = parts[1]

        return first_line if first_line else text.strip()

    def end_conversation(self) -> Dict[str, Any]:
        """
        End the current conversation session.

        Returns:
            Session summary
        """
        self.conversation_active = False

        # Update stats
        self.learner.stats.total_conversations += 1
        self.learner.stats.last_conversation = self.learner.last_updated

        # Get summaries
        session_summary = self.pedagogical_engine.get_session_summary()
        learner_summary = self.learner.get_learning_summary()

        return {
            "session": session_summary,
            "learner": learner_summary,
            "message": "Good practice session! See you next time.",
        }
