#!/usr/bin/env python3
"""
Example usage of the Language Learning Companion.

This demonstrates how to use the agent programmatically.
"""

import os
from dotenv import load_dotenv

from src.models.learner import Learner, ConfidenceLevel
from src.agents import AgentConfig, ConversationAgent
from src.llm.client import LLMClient
from src.memory.json_store import JSONMemoryStore

# Load environment variables
load_dotenv()


def example_conversation():
    """Example: Have a conversation with the agent."""

    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Please set ANTHROPIC_API_KEY in your environment or .env file")
        return

    # Create a learner
    learner = Learner(
        learner_id="example_learner",
        target_language="german",
        current_cefr_level="A1",
        confidence=ConfidenceLevel.MODERATE,
    )

    # Add some initial vocabulary
    learner.add_or_update_vocabulary("Hallo", "Hello", "interjection")
    learner.add_or_update_vocabulary("Wie", "How", "interrogative")
    learner.add_or_update_vocabulary("geht", "goes/go", "verb")

    # Initialize components
    llm_client = LLMClient()
    memory_store = JSONMemoryStore("./data")

    # Create agent
    config = AgentConfig(
        name="German Teacher",
        description="Conversation practice in German",
        target_language="german",
    )

    agent = ConversationAgent(
        config=config,
        learner=learner,
        llm_client=llm_client,
    )

    # Start conversation
    print("\n" + "="*50)
    print("Conversation Example")
    print("="*50 + "\n")

    opening = agent.start_conversation(topic="daily life")
    print(f"Teacher: {opening}\n")

    # Simulate some conversation turns
    learner_inputs = [
        "Ich bin Student",
        "Ich lerne Deutsch",
        "Was machst du?",
    ]

    for user_input in learner_inputs:
        print(f"You: {user_input}")

        result = agent.process({
            "learner_input": user_input,
            "conversation_context": {"topic": "daily life"}
        })

        print(f"Teacher: {result['response']}")

        if result["errors"]:
            print(f"  [Errors: {len(result['errors'])}]")

        print()

    # End conversation and show summary
    summary = agent.end_conversation()

    print("="*50)
    print("Session Summary")
    print("="*50)
    print(f"Turns: {summary['session']['turns']}")
    print(f"Errors: {summary['session']['errors']}")
    print(f"Flow score: {summary['session']['flow_score']}")

    # Save learner progress
    memory_store.save_learner(learner)
    print(f"\nLearner progress saved to: ./data/{learner.learner_id}.json")


def example_vocabulary_tracking():
    """Example: Track vocabulary learning."""

    print("\n" + "="*50)
    print("Vocabulary Tracking Example")
    print("="*50 + "\n")

    learner = Learner(
        learner_id="vocab_example",
        target_language="german",
    )

    # Add vocabulary through encounters
    words = [
        ("Haus", "house", "noun"),
        ("gehen", "to go", "verb"),
        ("sprechen", "to speak", "verb"),
    ]

    for word, translation, pos in words:
        item = learner.add_or_update_vocabulary(word, translation, pos, context="Example context")
        print(f"Added: {word} ({translation}) - Status: {item.status}")

    # Record some practice attempts
    vocab = learner.get_vocabulary("Haus")
    vocab.record_production(correct=True)
    vocab.record_production(correct=True)
    vocab.record_production(correct=False)

    print(f"\nAfter practicing 'Haus':")
    print(f"  Correct: {vocab.correct_productions}")
    print(f"  Incorrect: {vocab.incorrect_productions}")
    print(f"  Mastery score: {vocab.mastery_score:.1%}")
    print(f"  Status: {vocab.status}")

    # Get words to review
    to_review = learner.get_vocabulary_to_review()
    print(f"\nWords needing review: {len(to_review)}")


def example_grammar_tracking():
    """Example: Track grammar patterns."""

    print("\n" + "="*50)
    print("Grammar Tracking Example")
    print("="*50 + "\n")

    learner = Learner(
        learner_id="grammar_example",
        target_language="german",
    )

    # Record attempts at grammar patterns
    patterns = [
        ("word_order", True),   # Success
        ("word_order", False),  # Mistake
        ("word_order", False),  # Another mistake
        ("word_order", True),   # Got it
        ("word_order", True),   # Success
        ("cases", False),       # Struggling with cases
        ("cases", False),       # Still struggling
        ("cases", True),        # Getting better
    ]

    for pattern_name, success in patterns:
        learner.record_grammar_attempt(pattern_name, success)
        pattern = learner.get_grammar_pattern(pattern_name)
        print(f"{pattern_name}: {'✓' if success else '✗'} "
              f"(mastery: {pattern.mastery_score:.1%})")

    # Get weak areas
    weak = learner.get_weak_grammar_areas(threshold=0.6)
    print(f"\nWeak areas (needs practice):")
    for pattern in weak:
        print(f"  • {pattern.name}: {pattern.mastery_score:.1%} mastery "
              f"({pattern.error_rate:.1%} error rate)")


if __name__ == "__main__":
    print("Language Learning Companion - Examples")
    print("=" * 50)

    # Uncomment the examples you want to run:

    # example_vocabulary_tracking()
    # example_grammar_tracking()
    # example_conversation()

    print("\nTo run examples, uncomment them in the main block.")
    print("Make sure to set ANTHROPIC_API_KEY before running the conversation example.")
