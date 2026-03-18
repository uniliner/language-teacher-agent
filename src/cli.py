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
from agents import AgentConfig, ConversationAgent
from llm.client import LLMClient
from memory.json_store import JSONMemoryStore


class LanguageLearningCLI:
    """Command-line interface for language learning."""

    def __init__(self, data_dir: str = "./data"):
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
        self.learner: Optional[Learner] = None

        # Session state
        self.session_active = False

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
        )

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

                # Display response
                self.console.print(Panel(
                    result["response"],
                    title="[bold green]Language Teacher[/bold green]",
                    border_style="green"
                ))

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
            self.console.print("\n[bold yellow]Areas to work on:[/bold yellow]")
            for pattern in weak_areas[:5]:
                self.console.print(f"  • {pattern.name}: {pattern.mastery_score:.0%} mastery")

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


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Adaptive Language Learning Companion")
    parser.add_argument(
        "--data-dir",
        default="./data",
        help="Directory to store learner data"
    )
    args = parser.parse_args()

    # Ensure data directory exists
    Path(args.data_dir).mkdir(parents=True, exist_ok=True)

    # Run CLI
    cli = LanguageLearningCLI(data_dir=args.data_dir)
    cli.run()


if __name__ == "__main__":
    main()
