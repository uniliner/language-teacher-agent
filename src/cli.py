#!/usr/bin/env python3
"""
Command-line interface for the Language Learning Companion.

This is the main entry point for interacting with the adaptive language
learning agent.
"""

import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markdown import Markdown
from rich.table import Table

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from models.learner import Learner, ConfidenceLevel
from agents import AgentConfig, ConversationAgent, PronunciationTeachingAgent
from llm.client import LLMClient
from memory.json_store import JSONMemoryStore
from speech import AzureSpeechClient, SpeechConfig


class LanguageLearningCLI:
    """Command-line interface for language learning."""

    def __init__(self, data_dir: str = "./data", experimentation_mode: bool = False):
        """Initialize the CLI."""
        load_dotenv()

        # Validate API key
        if not os.getenv("ANTHROPIC_API_KEY"):
            console.print("[red]Error: ANTHROPIC_API_KEY not found in environment[/red]")
            console.print("\nPlease set your API key:")
            console.print("  export ANTHROPIC_API_KEY='your-key-here'")
            console.print("  # Or create a .env file with ANTHROPIC_API_KEY=your-key-here")
            sys.exit(1)

        # Initialize components
        self.console = Console()
        self.memory_store = JSONMemoryStore(data_dir)
        self.llm_client = None
        self.agent: Optional[ConversationAgent] = None
        self.pronunciation_agent: Optional[PronunciationTeachingAgent] = None
        self.learner: Optional[Learner] = None
        self.speech_client: Optional[AzureSpeechClient] = None

        # Session state
        self.session_active = False
        self.experimentation_mode = experimentation_mode

    def run(self):
        """Run the CLI application."""
        self._print_welcome()

        # Get or create learner
        learner_id = self._get_learner_id()
        self.learner = self._load_or_create_learner(learner_id)

        # Initialize LLM client
        try:
            self.llm_client = LLMClient()
        except Exception as e:
            self.console.print(f"[red]Failed to initialize LLM client: {e}[/red]")
            sys.exit(1)

        # Main menu
        while True:
            if not self._main_menu():
                break

    def run_pronunciation_practice_mode(self):
        """Run dedicated pronunciation practice mode."""
        self._print_welcome()

        # Get or create learner
        learner_id = self._get_learner_id()
        self.learner = self._load_or_create_learner(learner_id)

        # Initialize speech client
        speech_config = SpeechConfig.from_env()
        if not speech_config:
            self.console.print("[red]Azure Speech credentials not found. Please set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION in .env[/red]")
            sys.exit(1)

        try:
            self.speech_client = AzureSpeechClient(speech_config)
            self.console.print("[green]✓ Audio features enabled[/green]\n")
        except Exception as e:
            self.console.print(f"[red]Failed to initialize audio features: {e}[/red]")
            sys.exit(1)

        # Initialize pronunciation agent
        pronunciation_config = AgentConfig(
            name="Pronunciation Teacher",
            description="Teaches German pronunciation patterns",
            target_language="german",
        )
        self.pronunciation_agent = PronunciationTeachingAgent(
            config=pronunciation_config,
            learner=self.learner,
            speech_client=self.speech_client,
        )

        self.console.print(Panel(
            "[bold cyan]🎤 Pronunciation Practice Mode[/bold cyan]\n\n"
            "Practice your German pronunciation with:\n"
            "• Listen to native pronunciation examples\n"
            "• Record your own attempts\n"
            "• Get instant feedback and accuracy scores\n"
            "• Track your improvement over time",
            title="Pronunciation Mode",
            border_style="cyan"
        ))

        # Main practice loop
        while True:
            if not self._pronunciation_practice_menu():
                break

    def _pronunciation_practice_menu(self) -> bool:
        """Show pronunciation practice menu."""
        self.console.print("\n[bold]Pronunciation Practice Menu[/bold]")
        self.console.print("1. Practice specific pattern")
        self.console.print("2. Practice random pattern")
        self.console.print("3. View my pronunciation progress")
        self.console.print("4. Exit")

        choice = Prompt.ask(
            "\nChoose an option",
            choices=["1", "2", "3", "4"],
            default="4"
        )

        if choice == "1":
            self._practice_specific_pattern()
        elif choice == "2":
            self._practice_random_pattern()
        elif choice == "3":
            self._view_pronunciation_progress()
        elif choice == "4":
            return False

        return True

    def _practice_specific_pattern(self):
        """Practice a specific pronunciation pattern."""
        patterns = self.pronunciation_agent.get_all_patterns()

        if not patterns:
            self.console.print("[yellow]No pronunciation patterns available[/yellow]")
            return

        # Display pattern options
        self.console.print("\n[bold]Available Pronunciation Patterns:[/bold]\n")

        for i, pattern in enumerate(patterns, 1):
            examples_str = ", ".join(pattern.examples[:3])
            self.console.print(f"{i}. [cyan]{pattern.name}[/cyan] - {pattern.description}")
            self.console.print(f"   [dim]Examples: {examples_str}[/dim]\n")

        choice = Prompt.ask(
            "\nSelect a pattern (number)",
            default="1"
        )

        try:
            pattern_index = int(choice) - 1
            if 0 <= pattern_index < len(patterns):
                pattern = patterns[pattern_index]
                self._practice_pattern_interactive(pattern)
            else:
                self.console.print("[red]Invalid pattern number[/red]")
        except ValueError:
            self.console.print("[red]Invalid input[/red]")

    def _practice_random_pattern(self):
        """Practice a random pronunciation pattern."""
        import random

        patterns = self.pronunciation_agent.get_all_patterns()
        if not patterns:
            self.console.print("[yellow]No pronunciation patterns available[/yellow]")
            return

        pattern = random.choice(patterns)
        self.console.print(f"\n[dim]Selected: {pattern.name}[/dim]\n")
        self._practice_pattern_interactive(pattern)

    def _practice_pattern_interactive(self, pattern):
        """
        Interactive practice loop for a single pattern.

        Args:
            pattern: PronunciationPattern to practice
        """
        self.console.print(Panel(
            f"[bold]{pattern.name}[/bold]\n\n"
            f"{pattern.description}\n\n"
            f"[dim]Teaching Notes: {pattern.teaching_notes}[/dim]\n\n"
            f"[bold cyan]Examples:[/bold cyan] {', '.join(pattern.examples[:5])}",
            title=f"Practice: {pattern.name}",
            border_style="cyan"
        ))

        # Practice loop
        while True:
            self.console.print("\n[bold]Practice Options:[/bold]")
            self.console.print("1. Listen to example")
            self.console.print("2. Record your pronunciation")
            self.console.print("3. Try a different example word")
            self.console.print("4. Back to menu")

            choice = Prompt.ask(
                "\nChoose an option",
                choices=["1", "2", "3", "4"],
                default="1"
            )

            if choice == "1":
                # Play audio for first example
                example = pattern.examples[0]
                self.console.print(f"\n[blue]🔊 Playing pronunciation of: [cyan]{example}[/cyan][/blue]")
                audio = self.speech_client.synthesize_speech(example)
                if audio:
                    self.speech_client.play_audio(audio)
                else:
                    self.console.print("[yellow]Could not play audio[/yellow]")

            elif choice == "2":
                # Practice recording
                example = pattern.examples[0]
                self.console.print(f"\n[dim]Say: [cyan]{example}[/cyan][/dim]")
                self.console.print("[dim]Press Enter when ready...[/dim]")
                input()

                self.console.print("\n[red]🔴 Recording...[/red]")
                assessment = self.speech_client.assess_pronunciation(example)

                if assessment:
                    self._display_pronunciation_assessment(assessment)
                else:
                    self.console.print("[yellow]Could not assess pronunciation[/yellow]")

            elif choice == "3":
                # Show all examples and let user choose
                self.console.print(f"\n[bold]Example words:[/bold]")
                for i, example in enumerate(pattern.examples, 1):
                    self.console.print(f"{i}. {example}")

                ex_choice = Prompt.ask("\nChoose an example to practice", default="1")
                try:
                    ex_index = int(ex_choice) - 1
                    if 0 <= ex_index < len(pattern.examples):
                        chosen_example = pattern.examples[ex_index]
                        self.console.print(f"\n[blue]🔊 Playing: [cyan]{chosen_example}[/cyan][/blue]")
                        audio = self.speech_client.synthesize_speech(chosen_example)
                        if audio:
                            self.speech_client.play_audio(audio)

                        self.console.print(f"\n[dim]Say: [cyan]{chosen_example}[/cyan][/dim]")
                        self.console.print("[dim]Press Enter when ready...[/dim]")
                        input()

                        self.console.print("\n[red]🔴 Recording...[/red]")
                        assessment = self.speech_client.assess_pronunciation(chosen_example)

                        if assessment:
                            self._display_pronunciation_assessment(assessment)
                except (ValueError, IndexError):
                    self.console.print("[red]Invalid choice[/red]")

            elif choice == "4":
                break

    def _view_pronunciation_progress(self):
        """View pronunciation learning progress."""
        patterns = self.learner.pronunciation_patterns if hasattr(self.learner, 'pronunciation_patterns') else {}

        if not patterns:
            self.console.print("\n[dim]No pronunciation patterns practiced yet. Start practicing to track your progress![/dim]")
            return

        self.console.print("\n[bold]Pronunciation Progress:[/bold]\n")

        table = Table(show_header=True)
        table.add_column("Pattern", style="cyan")
        table.add_column("Mastery", style="magenta")
        table.add_column("Practices", style="yellow")

        for pattern_id, pattern in patterns.items():
            mastery_percentage = pattern.mastery_score * 100
            if mastery_percentage >= 80:
                mastery_style = "green"
            elif mastery_percentage >= 60:
                mastery_style = "yellow"
            else:
                mastery_style = "red"

            table.add_row(
                pattern.name,
                f"[{mastery_style}]{mastery_percentage:.1f}%[/{mastery_style}]",
                str(pattern.practice_count)
            )

        self.console.print(table)

    def _print_welcome(self):
        """Print welcome message."""
        welcome_text = """
# Willkommen! Welcome! 🎓

This is your **Adaptive Language Learning Companion**.

I conduct natural conversations in your target language while tracking:
- 📚 Your vocabulary growth
- 🧠 Grammar pattern mastery
- 😊 Your confidence level
- 📈 Progress over time

I autonomously decide when to introduce new material, when to correct
errors, and when to let the conversation flow naturally.

Let's get started!
"""
        self.console.print(Panel(Markdown(welcome_text), title="Language Teacher", border_style="blue"))

    def _get_learner_id(self) -> str:
        """Get learner ID from user."""
        self.console.print("\n[bold]Learner Identification[/bold]")

        # List existing learners
        existing = self.memory_store.list_learners()
        if existing:
            self.console.print("\nExisting learners:")
            for learner_id in existing:
                self.console.print(f"  • {learner_id}")

        learner_id = Prompt.ask(
            "\nEnter your name (or learner ID)",
            default="learner",
            show_default=False
        ).strip()

        if not learner_id:
            learner_id = "learner"

        return learner_id.lower().replace(" ", "_")

    def _load_or_create_learner(self, learner_id: str) -> Learner:
        """Load existing learner or create new one."""
        if self.memory_store.learner_exists(learner_id):
            self.console.print(f"\n[green]Welcome back, {learner_id}![/green]")
            learner = self.memory_store.load_learner(learner_id)

            # Show progress summary
            summary = learner.get_learning_summary()
            self._print_progress_summary(summary)
        else:
            self.console.print(f"\n[blue]Creating new profile for {learner_id}...[/blue]")

            # Get initial level
            level = Prompt.ask(
                "What's your current German level?",
                choices=["A1", "A2", "B1", "B2", "C1", "C2"],
                default="A1"
            )

            learner = Learner(
                learner_id=learner_id,
                target_language="german",
                native_language="english",
                current_cefr_level=level,
                confidence=ConfidenceLevel.MODERATE,
            )

            self.memory_store.save_learner(learner)
            self.console.print("[green]Profile created![/green]")

        return learner

    def _print_progress_summary(self, summary: dict):
        """Print learner progress summary."""
        table = Table(title="Your Progress", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")

        for key, value in summary.items():
            if key != "last practiced":
                table.add_row(key.replace("_", " ").title(), str(value))

        self.console.print(table)

    def _main_menu(self) -> bool:
        """Display main menu and return choice."""
        self.console.print("\n" + "="*50)
        self.console.print("[bold]Main Menu[/bold]")
        self.console.print("="*50)
        self.console.print("1. Start Conversation")
        self.console.print("2. View Progress")
        self.console.print("3. Practice Vocabulary")
        self.console.print("4. Settings")
        self.console.print("5. Exit")

        choice = Prompt.ask(
            "\nWhat would you like to do?",
            choices=["1", "2", "3", "4", "5"],
            default="1"
        )

        if choice == "1":
            self._start_conversation()
        elif choice == "2":
            self._view_progress()
        elif choice == "3":
            self._practice_vocabulary()
        elif choice == "4":
            self._settings()
        elif choice == "5":
            return False

        return True

    def _start_conversation(self):
        """Start a conversation session."""
        # Create agent
        config = AgentConfig(
            name="German Conversation Partner",
            description="Conversational practice in German",
            target_language="german",
        )

        self.agent = ConversationAgent(
            config=config,
            learner=self.learner,
            llm_client=self.llm_client,
            experimentation_mode=self.experimentation_mode,
        )

        # Initialize speech client for audio features
        speech_config = SpeechConfig.from_env()
        if speech_config:
            try:
                self.speech_client = AzureSpeechClient(speech_config)
                self.console.print("[green]✓ Audio features enabled[/green]")
            except Exception as e:
                self.console.print(f"[yellow]⚠ Could not initialize audio features: {e}[/yellow]")
                self.console.print("[dim]Continuing without audio...[/dim]\n")
        else:
            self.console.print("[dim]No Azure Speech credentials found. Audio features disabled.[/dim]\n")

        # Initialize pronunciation teaching agent
        pronunciation_config = AgentConfig(
            name="Pronunciation Teacher",
            description="Teaches German pronunciation patterns",
            target_language="german",
        )
        self.pronunciation_agent = PronunciationTeachingAgent(
            config=pronunciation_config,
            learner=self.learner,
            llm_client=self.llm_client,
            speech_client=self.speech_client,
        )

        # Show experimentation mode notice
        if self.experimentation_mode:
            self.console.print("\n[yellow bold]🧪 Experimentation Mode Active[/yellow bold]")
            self.console.print("[dim]Pedagogical triggers are accelerated for testing:[/dim]")
            self.console.print("[dim]  • New material: every 2 turns (vs 10)[/dim]")
            self.console.print("[dim]  • Reviews: every 3 turns (vs 8)[/dim]")
            self.console.print("[dim]  • Minimum intro time: 30s (vs 3 min)[/dim]")
            self.console.print("[dim]  • Pronunciation: every 3 turns (vs 15)[/dim]\n")
            self.console.print("\n[yellow bold]🧪 Experimentation Mode Active[/yellow bold]")
            self.console.print("[dim]Pedagogical triggers are accelerated for testing:[/dim]")
            self.console.print("[dim]  • New material: every 2 turns (vs 10)[/dim]")
            self.console.print("[dim]  • Reviews: every 3 turns (vs 8)[/dim]")
            self.console.print("[dim]  • Minimum intro time: 30s (vs 3 min)[/dim]\n")

        # Ask for topic
        self.console.print("\n[bold cyan]Starting conversation...[/bold cyan]")
        topic = Prompt.ask(
            "Enter a topic (or press Enter for free conversation)",
            default=""
        ).strip() or None

        # Start conversation
        opening = self.agent.start_conversation(topic)
        self.console.print(Panel(
            opening,
            title="[bold green]Language Teacher[/bold green]",
            border_style="green"
        ))

        # Conversation loop
        self.session_active = True
        while self.session_active:
            # Get user input
            user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]", default="").strip()

            if not user_input:
                continue

            # Check for exit commands
            if user_input.lower() in ["exit", "quit", "bye", "goodbye"]:
                self._end_conversation()
                break

            # Process input
            try:
                result = self.agent.process({
                    "learner_input": user_input,
                    "conversation_context": {
                        "topic": topic,
                    }
                })

                # Check if this is a pronunciation teaching decision
                if result.get("teaching_action") == "teach_pronunciation":
                    # Route to pronunciation agent
                    # Extract recent words from vocabulary analysis
                    analysis_data = result.get("metadata", {})
                    recent_words = []
                    # We'll pass an empty list for now; the pronunciation agent
                    # can also select patterns independently of recent words

                    pronunciation_result = self.pronunciation_agent.process({
                        "learner": self.learner,
                        "conversation_state": {"topic": topic},
                        "recent_words": recent_words,
                        "decision": result.get("teaching_decision"),
                    })

                    # Display pronunciation tip
                    if pronunciation_result.get("explanation"):
                        practice_word = pronunciation_result.get('practice_word', '')

                        # Play audio if available
                        if pronunciation_result.get("audio_data") and self.speech_client:
                            self.console.print("\n[blue]🔊 Playing pronunciation example...[/blue]")
                            self.speech_client.play_audio(pronunciation_result["audio_data"])

                        # Display the tip
                        self.console.print(Panel(
                            f"🎤 [bold]Pronunciation Tip:[/bold]\n\n{pronunciation_result['explanation']}\n\n"
                            f"Practice word: [bold cyan]{practice_word}[/bold cyan]",
                            title="[bold magenta]Pronunciation[/bold magenta]",
                            border_style="magenta"
                        ))

                        # Offer practice opportunity if speech client available
                        if self.speech_client and practice_word:
                            self._offer_pronunciation_practice(practice_word, pronunciation_result.get('pattern_id'))

                    # Continue with conversation response
                    self.console.print(Panel(
                        result["response"],
                        title="[bold green]Language Teacher[/bold green]",
                        border_style="green"
                    ))
                else:
                    # Display normal response
                    self.console.print(Panel(
                        result["response"],
                        title="[bold green]Language Teacher[/bold green]",
                        border_style="green"
                    ))

                # Show pedagogical action in experimentation mode
                if self.experimentation_mode and result.get("teaching_action"):
                    action_colors = {
                        "correct": "red",
                        "introduce": "blue",
                        "review": "yellow",
                        "continue": "green",
                        "simplify": "magenta",
                        "teach_pronunciation": "cyan"
                    }
                    action_color = action_colors.get(result["teaching_action"], "white")
                    self.console.print(f"\n[dim][{action_color}]Action: {result['teaching_action'].upper()}[/{action_color}][/dim]")

                # Show errors if any and in learning mode
                if result["errors"] and self.learner.correction_sensitivity != "gentle":
                    self.console.print(f"\n[dim]Errors detected: {len(result['errors'])}[/dim]")
                    for error in result["errors"][:2]:  # Show max 2
                        self.console.print(f"  [dim]• {error.get('description', '')}[/dim]")

            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")
                continue

        # Save learner state
        self.memory_store.save_learner(self.learner)

    def _end_conversation(self):
        """End the conversation session."""
        if not self.agent:
            return

        summary = self.agent.end_conversation()

        self.console.print("\n" + "="*50)
        self.console.print("[bold yellow]Session Summary[/bold yellow]")
        self.console.print("="*50)
        if summary['session'].get('experimentation_mode'):
            self.console.print("[yellow]🧪 Experimentation Mode[/yellow]")
        self.console.print(f"Turns: {summary['session']['turns']}")
        self.console.print(f"Errors: {summary['session']['errors']}")
        self.console.print(f"Error rate: {summary['session']['error_rate']:.1%}")
        self.console.print(f"Flow score: {summary['session']['flow_score']}")
        self.console.print(f"\n{summary['message']}")

        self.session_active = False

    def _view_progress(self):
        """View detailed progress."""
        summary = self.learner.get_learning_summary()

        self.console.print("\n[bold]Learning Progress[/bold]\n")

        # Overall stats
        self.console.print(f"Level: {summary['level']}")
        self.console.print(f"Confidence: {summary['confidence']}")
        self.console.print(f"Vocabulary: {summary['vocabulary_size']} words")
        self.console.print(f"Mastered: {summary.get('words mastered', 0)} words")
        self.console.print(f"Grammar patterns: {summary.get('grammar patterns', 0)}")
        self.console.print(f"Overall mastery: {summary['overall mastery']}")
        self.console.print(f"Total conversations: {summary['total conversations']}")

        # Vocabulary breakdown
        if self.learner.vocabulary:
            self.console.print("\n[bold]Vocabulary by Mastery:[/bold]")

            from models.vocabulary import VocabularyStatus
            status_counts = {}
            for item in self.learner.vocabulary.values():
                status = item.status
                status_counts[status] = status_counts.get(status, 0) + 1

            for status in VocabularyStatus:
                count = status_counts.get(status, 0)
                if count > 0:
                    self.console.print(f"  {status.value}: {count}")

        # Grammar weaknesses
        weak_areas = self.learner.get_weak_grammar_areas(threshold=0.6)
        if weak_areas:
            self.console.print("\n[bold yellow]Grammar areas to work on:[/bold yellow]")
            for pattern in weak_areas[:5]:
                self.console.print(f"  • {pattern.name}: {pattern.mastery_score:.0%} mastery")

        # Pronunciation progress
        if self.learner.pronunciation_patterns:
            self.console.print(f"\n[bold]Pronunciation patterns learned: {len(self.learner.pronunciation_patterns)}[/bold]")

            pronunciation_mastery = self.learner.calculate_pronunciation_mastery()
            self.console.print(f"Overall pronunciation mastery: {pronunciation_mastery:.0%}")

            # Show patterns needing review
            to_review = self.learner.get_pronunciation_patterns_to_review()
            if to_review:
                self.console.print("\n[bold yellow]Pronunciation patterns to review:[/bold yellow]")
                for pattern in to_review[:5]:
                    self.console.print(f"  • {pattern.name}: {pattern.mastery_score:.0%} mastery")
        else:
            self.console.print("\n[dim]No pronunciation patterns learned yet. Practice more to see pronunciation tips![/dim]")

    def _practice_vocabulary(self):
        """Practice vocabulary that needs review."""
        to_review = self.learner.get_vocabulary_to_review()

        if not to_review:
            self.console.print("\n[green]No vocabulary due for review![/green]")
            return

        self.console.print(f"\n[bold]Vocabulary to Review ({len(to_review)} items)[/bold]")

        for item in to_review[:10]:  # Show max 10
            self.console.print(f"\n• [bold]{item.word}[/bold]")
            self.console.print(f"  Translation: {item.translation}")
            self.console.print(f"  Status: {item.status}")
            self.console.print(f"  Encountered: {item.encounters_count} times")

    def _settings(self):
        """Settings menu."""
        self.console.print("\n[bold]Settings[/bold]")
        self.console.print(f"Current level: {self.learner.current_cefr_level}")
        self.console.print(f"Confidence: {self.learner.confidence}")
        self.console.print(f"Correction sensitivity: {self.learner.correction_sensitivity}")

        change = Prompt.ask(
            "\nChange level?",
            choices=["yes", "no"],
            default="no"
        )

        if change == "yes":
            new_level = Prompt.ask(
                "New level",
                choices=["A1", "A2", "B1", "B2", "C1", "C2"],
                default=self.learner.current_cefr_level
            )
            self.learner.current_cefr_level = new_level
            self.memory_store.save_learner(self.learner)
            self.console.print("[green]Level updated![/green]")

    def _offer_pronunciation_practice(self, practice_word: str, pattern_id: Optional[str] = None):
        """
        Offer the user a chance to practice pronunciation with recording and assessment.

        Args:
            practice_word: The word to practice
            pattern_id: Optional pattern ID being practiced
        """
        if not self.speech_client:
            return

        # Ask if user wants to practice
        practice = Prompt.ask(
            "\n🎤 Would you like to practice your pronunciation?",
            choices=["yes", "no"],
            default="no"
        )

        if practice != "yes":
            return

        self.console.print("\n[bold]Pronunciation Practice[/bold]")
        self.console.print(f"[dim]Say this word: [cyan]{practice_word}[/cyan][/dim]")
        self.console.print("[dim]Press Enter when ready to speak...[/dim]")

        input()  # Wait for user to press Enter

        # Record pronunciation
        self.console.print("\n[red]🔴 Recording... Speak now![/red]")
        assessment = self.speech_client.assess_pronunciation(practice_word)

        if assessment:
            # Display assessment results
            self._display_pronunciation_assessment(assessment)
        else:
            self.console.print("[yellow]⚠ Could not assess pronunciation. Please try again.[/yellow]")

    def _display_pronunciation_assessment(self, assessment):
        """
        Display pronunciation assessment results with visual feedback.

        Args:
            assessment: PronunciationAssessmentResult object
        """
        from rich.table import Table
        from rich.progress import Progress, BarColumn, TextColumn

        # Create results table
        table = Table(title="\n📊 Pronunciation Assessment Results", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Score", style="magenta")
        table.add_column("Grade", style="green")

        # Add scores with color coding
        scores = {
            "Accuracy": assessment.accuracy_score,
            "Fluency": assessment.fluency_score,
            "Completeness": assessment.completeness_score,
            "Prosody": assessment.prosody_score,
        }

        for metric, score in scores.items():
            percentage = score * 100
            if percentage >= 90:
                grade = "A"
                style = "green"
            elif percentage >= 80:
                grade = "B"
                style = "blue"
            elif percentage >= 70:
                grade = "C"
                style = "yellow"
            elif percentage >= 60:
                grade = "D"
                style = "orange"
            else:
                grade = "F"
                style = "red"

            table.add_row(metric, f"{percentage:.1f}%", f"[{style}]{grade}[/{style}]")

        self.console.print(table)

        # Overall score
        overall = assessment.overall_score * 100
        self.console.print(f"\n[bold]Overall Score: {overall:.1f}%[/bold]")

        # Feedback message
        feedback = assessment.get_feedback_message()
        self.console.print(f"\n{feedback}")

        # Error text if available (what was actually heard)
        if assessment.error_text and assessment.error_text != assessment.error_text:
            self.console.print(f"\n[dim]We heard: \"{assessment.error_text}\"[/dim]")

        self.console.print()  # Blank line


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Adaptive Language Learning Companion")
    parser.add_argument(
        "--data-dir",
        default="./data",
        help="Directory to store learner data"
    )
    parser.add_argument(
        "--experiment", "--fast",
        action="store_true",
        help="Enable experimentation mode with accelerated pedagogical triggers for testing"
    )
    parser.add_argument(
        "--pronunciation-mode",
        action="store_true",
        help="Launch dedicated pronunciation practice mode for focused pronunciation exercises"
    )
    args = parser.parse_args()

    # Ensure data directory exists
    Path(args.data_dir).mkdir(parents=True, exist_ok=True)

    # Run CLI
    cli = LanguageLearningCLI(data_dir=args.data_dir, experimentation_mode=args.experiment)

    # Launch pronunciation practice mode if requested
    if args.pronunciation_mode:
        cli.run_pronunciation_practice_mode()
    else:
        cli.run()


if __name__ == "__main__":
    main()
