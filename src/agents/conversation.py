"""
Conversation agent for natural language practice.

This agent conducts conversations in the target language while
tracking learner progress and making pedagogical decisions.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from .base import Agent, AgentConfig
from .grammar_curriculum import GrammarCurriculumAgent
from .pronunciation_teaching import PronunciationTeachingAgent
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
        pronunciation_teaching_agent: Optional[PronunciationTeachingAgent] = None,
        experimentation_mode: bool = False,
    ):
        super().__init__(config, learner, llm_client)

        # Pedagogical engine (still used for some utility functions)
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

        # Pronunciation teaching agent (create if not provided)
        pronunciation_config = AgentConfig(
            name="pronunciation_teaching",
            description="Teaches pronunciation patterns and tracks progress",
            target_language=config.target_language,
        )
        self.pronunciation_teaching_agent = pronunciation_teaching_agent or PronunciationTeachingAgent(
            config=pronunciation_config,
            learner=learner,
            llm_client=llm_client,
        )

        # Conversation state
        self.conversation_active = False
        self.current_topic: Optional[str] = None
        self.turns_in_session = 0

        # Track orchestration for debugging/analysis
        self.orchestration_history: List[Dict[str, Any]] = []

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
        Process learner input and generate response using agentic ReAct loop.

        This replaces the old fixed pipeline with a truly agentic approach:
        1. OBSERVE: Analyze input and gather context
        2. REASON: LLM decides what the learner needs and which specialists to call
        3. ACT: Call specialist agents as needed
        4. SYNTHESIZE: Generate final response combining all insights
        5. UPDATE: Update learner state

        Args:
            input_data: Dictionary containing:
                - learner_input: What the learner said
                - conversation_context: Current conversation state

        Returns:
            Dictionary with:
                - response: Agent's response
                - errors: Errors detected (if any)
                - orchestration: How the orchestrator decided to handle this turn
                - updated_state: Changes to learner state
        """
        learner_input = input_data.get("learner_input", "")
        conversation_context = input_data.get("conversation_context", {})

        # ========================================================================
        # STEP 1: OBSERVE - Gather all relevant information
        # ========================================================================
        print(f"\n[Orchestrator] Step 1: OBSERVE - Analyzing learner input...")
        analysis = self._analyze_input(learner_input)

        # Build learner state summary for orchestration
        learner_state = self._get_learner_state_summary()
        conversation_context_enhanced = {
            **conversation_context,
            "turn_number": self.turns_in_session,
            "flow_score": self.pedagogical_engine.conversation_flow_score,
        }

        # ========================================================================
        # STEP 2: REASON - LLM decides what to do and which specialists to call
        # ========================================================================
        print(f"[Orchestrator] Step 2: REASON - Determining teaching strategy...")

        orchestration = self.llm_client.generate_orchestration_plan(
            learner_input=learner_input,
            detected_errors=analysis.get("errors", []),
            learner_state=learner_state,
            conversation_context=conversation_context_enhanced,
        )

        print(f"[Orchestrator] Reasoning: {orchestration.get('thoughts', 'N/A')}")
        print(f"[Orchestrator] Strategy: {orchestration.get('teaching_strategy', 'N/A')}")
        print(f"[Orchestrator] Actions: {len(orchestration.get('actions', []))} specialist(s) to call")

        # ========================================================================
        # STEP 3: ACT - Call specialist agents as decided by the orchestrator
        # ========================================================================
        print(f"[Orchestrator] Step 3: ACT - Calling specialist agents...")

        specialist_results = {}

        # Sort actions by priority (1=highest)
        actions = sorted(
            orchestration.get("actions", []),
            key=lambda a: a.get("priority", 99)
        )

        for action in actions:
            specialist_name = action.get("specialist")
            purpose = action.get("purpose")

            print(f"[Orchestrator]   → Calling {specialist_name} (purpose: {purpose})")

            result = self._call_specialist(
                specialist_name=specialist_name,
                purpose=purpose,
                learner_input=learner_input,
                analysis=analysis,
                conversation_context=conversation_context_enhanced,
            )

            specialist_results[specialist_name] = result

        # ========================================================================
        # STEP 4: SYNTHESIZE - Generate final response
        # ========================================================================
        print(f"[Orchestrator] Step 4: SYNTHESIZE - Generating response...")

        response = self._synthesize_response(
            learner_input=learner_input,
            orchestration=orchestration,
            specialist_results=specialist_results,
            analysis=analysis,
            conversation_context=conversation_context_enhanced,
        )

        # ========================================================================
        # STEP 5: UPDATE - Update learner state
        # ========================================================================
        print(f"[Orchestrator] Step 5: UPDATE - Updating learner state...")

        updated_state = self._update_learner_from_specialists(
            specialist_results=specialist_results,
            analysis=analysis,
            orchestration=orchestration,
        )

        # Update conversation history
        self._add_to_conversation_history(learner_input, response, analysis)

        # Track orchestration for analysis
        self.orchestration_history.append({
            "turn": self.turns_in_session,
            "orchestration": orchestration,
            "specialists_called": list(specialist_results.keys()),
            "errors_count": len(analysis.get("errors", [])),
        })

        # Update pedagogical engine state (for flow tracking, etc.)
        self.pedagogical_engine.turn_count += 1
        self.pedagogical_engine.error_count += len(analysis.get("errors", []))

        self.turns_in_session += 1

        return {
            "response": response,
            "errors": analysis.get("errors", []),
            "orchestration": orchestration,
            "specialist_results": specialist_results,
            "updated_state": updated_state,
            "metadata": {
                "agent": self.config.name,
                "turn": self.turns_in_session,
                "specialists_called": list(specialist_results.keys()),
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

    def _get_learner_state_summary(self) -> Dict[str, Any]:
        """
        Get a summary of learner state for orchestration.

        Returns:
            Dictionary with relevant learner state information
        """
        return {
            "confidence": str(self.learner.confidence),
            "cefr_level": self.learner.current_cefr_level,
            "total_turns": self.learner.stats.total_turns,
            "vocabulary_size": len(self.learner.vocabulary),
            "grammar_patterns": {
                name: {
                    "mastery_score": pattern.mastery_score,
                    "attempts": pattern.attempts,
                }
                for name, pattern in self.learner.grammar_patterns.items()
            },
            "recent_error_rate": (
                self.pedagogical_engine.error_count / max(self.pedagogical_engine.turn_count, 1)
                if self.pedagogical_engine.turn_count > 0
                else 0.0
            ),
        }

    def _call_specialist(
        self,
        specialist_name: str,
        purpose: str,
        learner_input: str,
        analysis: Dict[str, Any],
        conversation_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Call a specialist agent and return its result.

        Args:
            specialist_name: Name of the specialist to call
            purpose: Why we're calling this specialist
            learner_input: What the learner said
            analysis: Input analysis results
            conversation_context: Conversation context

        Returns:
            Result from the specialist agent
        """
        try:
            if specialist_name == "grammar_curriculum":
                return self.grammar_curriculum_agent.process({
                    "errors": analysis.get("errors", []),
                    "learner_input": learner_input,
                    "purpose": purpose,
                })

            elif specialist_name == "pronunciation_teaching":
                # Get recent words from analysis
                recent_words = [
                    v.get("word") if isinstance(v, dict) else v
                    for v in analysis.get("vocabulary_used", [])
                ]

                return self.pronunciation_teaching_agent.process({
                    "learner": self.learner,
                    "conversation_state": conversation_context,
                    "recent_words": recent_words,
                    "purpose": purpose,
                })

            else:
                print(f"[Orchestrator] Warning: Unknown specialist '{specialist_name}'")
                return {"error": f"Unknown specialist: {specialist_name}"}

        except Exception as e:
            print(f"[Orchestrator] Error calling {specialist_name}: {e}")
            return {"error": str(e)}

    def _synthesize_response(
        self,
        learner_input: str,
        orchestration: Dict[str, Any],
        specialist_results: Dict[str, Any],
        analysis: Dict[str, Any],
        conversation_context: Dict[str, Any],
    ) -> str:
        """
        Synthesize final response from orchestration and specialist results.

        Args:
            learner_input: What the learner said
            orchestration: Orchestration decision from LLM
            specialist_results: Results from specialist agents
            analysis: Input analysis results
            conversation_context: Conversation context

        Returns:
            Final response to learner
        """
        if not self.llm_client:
            return f"I understand: {learner_input}. Let's continue!"

        try:
            # Build context for response generation
            response_context = {
                "learner_input": learner_input,
                "orchestration": orchestration,
                "specialist_results": specialist_results,
                "errors": analysis.get("errors", []),
                "confidence": self.learner.confidence,
                "cefr_level": self.learner.current_cefr_level,
                "topic": self.current_topic,
                "flow_score": conversation_context.get("flow_score", 0.5),
            }

            response = self.llm_client.generate_teaching_response(
                learner_input=learner_input,
                decision=self._create_teaching_decision_from_orchestration(
                    orchestration, specialist_results
                ),
                conversation_context=response_context,
                target_language=self.config.target_language,
            )

            return response

        except Exception as e:
            print(f"Error synthesizing response: {e}")
            return "Es tut mir leid, could you please repeat that?"

    def _create_teaching_decision_from_orchestration(
        self,
        orchestration: Dict[str, Any],
        specialist_results: Dict[str, Any],
    ) -> TeachingDecision:
        """
        Create a TeachingDecision from orchestration results.

        This bridges the new agentic system with the existing TeachingDecision format
        that the LLMClient's generate_teaching_response() expects.

        Args:
            orchestration: Orchestration decision
            specialist_results: Results from specialists

        Returns:
            TeachingDecision for compatibility
        """
        from pedagogy.strategies import TeachingStrategy

        # Map orchestration strategy to TeachingStrategy enum
        strategy_map = {
            "gentle_correction": TeachingStrategy.GENTLE_RECAST,
            "explicit_explanation": TeachingStrategy.Explicit_explanation,
            "pattern_highlighting": TeachingStrategy.Pattern_highlighting,
            "spaced_repetition": TeachingStrategy.SPACED_REPETITION,
            "challenge_providing": TeachingStrategy.CHALLENGE_PROVIDING,
            "confidence_building": TeachingStrategy.CONFIDENCE_BUILDING,
            "flow_preservation": TeachingStrategy.FLOW_PRESERVATION,
        }

        strategy = strategy_map.get(
            orchestration.get("teaching_strategy"),
            TeachingStrategy.FLOW_PRESERVATION
        )

        # Determine action based on what specialists were called
        actions_called = [r.get("specialist", a.get("specialist"))
                         for r, a in zip(specialist_results.values(), orchestration.get("actions", []))]

        if "pronunciation_teaching" in actions_called:
            action = "teach_pronunciation"
        elif any("grammar" in str(a) for a in actions_called):
            action = "correct"  # or "introduce" or "review"
        else:
            action = "continue"

        # Build metadata from specialist results
        metadata = {
            "orchestration_thoughts": orchestration.get("thoughts"),
            "orchestration_confidence": orchestration.get("confidence"),
            "response_guidance": orchestration.get("response_guidance"),
            "specialists_called": actions_called,
        }

        # Add specialist-specific metadata
        if "grammar_curriculum" in specialist_results:
            grammar_result = specialist_results["grammar_curriculum"]
            metadata["grammar_updates"] = grammar_result.get("patterns_updated", [])
            metadata["ready_to_advance"] = grammar_result.get("ready_to_advance", False)

        if "pronunciation_teaching" in specialist_results:
            pron_result = specialist_results["pronunciation_teaching"]
            metadata["pronunciation_pattern"] = pron_result.get("pattern_id")

        return TeachingDecision(
            action=action,
            strategy=strategy,
            content=None,
            metadata=metadata,
        )

    def _update_learner_from_specialists(
        self,
        specialist_results: Dict[str, Any],
        analysis: Dict[str, Any],
        orchestration: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update learner state from specialist results.

        Args:
            specialist_results: Results from specialist agents
            analysis: Input analysis results
            orchestration: Orchestration decision

        Returns:
            Dictionary of state updates
        """
        updates = {}

        # Vocabulary updates (from analysis)
        vocabulary_data = analysis.get("vocabulary_used", [])
        for vocab_item_data in vocabulary_data:
            if isinstance(vocab_item_data, str):
                word = vocab_item_data
                translation = ""
                part_of_speech = "unknown"
            else:
                word = vocab_item_data.get("word", "")
                translation = vocab_item_data.get("translation", "")
                part_of_speech = vocab_item_data.get("part_of_speech", "unknown")

            if not word:
                continue

            vocab_item = self.learner.get_vocabulary(word)
            if vocab_item:
                vocab_item.record_encounter(context=self.learner.recent_conversations[-1].get("learner_input", "")[:50] if self.learner.recent_conversations else "")
            elif translation:
                self.learner.add_or_update_vocabulary(
                    word=word,
                    translation=translation,
                    part_of_speech=part_of_speech,
                    context=self.learner.recent_conversations[-1].get("learner_input", "")[:50] if self.learner.recent_conversations else "",
                )

        # Grammar updates (from grammar_curriculum specialist)
        if "grammar_curriculum" in specialist_results:
            grammar_result = specialist_results["grammar_curriculum"]
            if grammar_result.get("patterns_updated"):
                updates["grammar_patterns_updated"] = grammar_result["patterns_updated"]
                updates["ready_to_advance"] = grammar_result.get("ready_to_advance", False)
                updates["suggested_focus"] = grammar_result.get("suggested_focus")

        # Pronunciation updates (from pronunciation_teaching specialist)
        if "pronunciation_teaching" in specialist_results:
            pron_result = specialist_results["pronunciation_teaching"]
            if pron_result.get("updated_state"):
                updates.update(pron_result["updated_state"])

        # Confidence updates
        error_count = len(analysis.get("errors", []))
        total_turns = self.pedagogical_engine.turn_count
        recent_success = error_count < total_turns * 0.3 if total_turns > 0 else True

        old_confidence = self.learner.confidence
        self.learner.update_confidence(error_count, total_turns, recent_success)

        if old_confidence != self.learner.confidence:
            updates["confidence"] = self.learner.confidence

        # Update stats
        self.learner.last_updated = datetime.now()

        return updates

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
