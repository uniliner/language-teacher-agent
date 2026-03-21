# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

An AI-powered language learning agent with a multi-agent architecture. The system conducts natural conversations in the target language (currently German) while tracking vocabulary, grammar patterns, and learner confidence to provide personalized, adaptive instruction.

## Development Commands

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Run the application
python -m src

# Run tests
pytest

# Run tests with coverage
pytest --cov=src

# Format code
black src tests

# Type checking
mypy src
```

## Environment Setup

The application requires an `ANTHROPIC_API_KEY` environment variable. Copy `.env.example` to `.env` and add your key, or export it directly:

```bash
export ANTHROPIC_API_KEY="your-key-here"
```

Learner data is stored in the `data/` directory (configurable via `--data-dir`).

## Architecture

### Multi-Agent Design

The codebase uses a specialized multi-agent architecture where different agents handle specific aspects of language learning:

- **`src/agents/base.py`**: Abstract `Agent` base class defining the interface all agents must implement (`process()`, `get_capabilities()`)
- **`src/agents/conversation.py`**: `ConversationAgent` for natural conversation practice

Future agents (PronunciationAgent, GrammarAgent, VocabularyAgent) can be added by extending the base `Agent` class.

### Core Components

**Pedagogical Engine** (`src/pedagogy/engine.py`): The decision-making brain that analyzes each conversation turn and decides what to do next:
- Whether to correct errors or preserve conversation flow
- When to introduce new material
- When to recycle/review previous vocabulary and grammar
- Tracks `conversation_flow_score` (0.0 = struggling, 1.0 = flowing)

**Models** (`src/models/`):
- `learner.py`: `Learner` state including confidence level, CEFR level, vocabulary, grammar patterns
- `vocabulary.py`: `VocabularyItem` with spaced repetition (SM-2 algorithm), mastery scoring, encounter/production tracking
- `grammar.py`: `GrammarPattern` with attempt/error tracking, mastery scoring

**LLM Client** (`src/llm/client.py`): Wrapper around Anthropic's Claude API for:
- `analyze_learner_input()`: Error detection and analysis
- `generate_teaching_response()`: Pedagogically-informed response generation
- Conversation history management

**Memory Store** (`src/memory/`): Pluggable persistence layer. Currently `JSONMemoryStore` saves/loads learner state as JSON.

### Data Flow: Conversation Turn

1. User input → CLI → `Agent.process()`
2. Agent → `LLMClient.analyze_learner_input()` (detect errors, vocabulary)
3. Agent → `PedagogicalEngine.analyze_turn()` (decide teaching action)
4. Engine → `StrategySelector` (choose correction/introduction/continue strategy)
5. Agent → `LLMClient.generate_teaching_response()` (create response)
6. Agent updates `Learner` state (vocabulary, grammar, confidence)
7. `MemoryStore.save_learner()` persists state

## Key Design Principles

1. **Bottom-Up Curriculum**: No pre-set lessons. Content emerges from conversation and learner interactions.

2. **Flow-Aware Correction**: The pedagogical engine tracks conversation flow and suppresses corrections when flow is low (< 0.3) or learner confidence is very low.

3. **Confidence Tracking**: `ConfidenceLevel` enum (VERY_LOW to VERY_HIGH) adjusts difficulty. Low confidence → confidence building strategies; high confidence → challenge providing.

4. **Spaced Repetition**: Vocabulary items use SM-2 algorithm for scheduling reviews based on performance.

5. **Pluggable Storage**: The `MemoryStore` interface allows swapping JSON for SQL, Redis, etc.

## File Structure Notes

- Entry points: `src/__main__.py` (for `python -m src`) and `src/cli.py` (main function)
- Agents in `src/agents/` follow the base class pattern
- Models in `src/models/` use pydantic for validation
- Teaching strategies defined in `src/pedagogy/strategies.py` as enum `TeachingStrategy`
- Prompts for LLM interactions are in `src/llm/prompts.py`

## Adding New Agents

To add a new agent type:

1. Create a new class in `src/agents/` inheriting from `Agent`
2. Implement `process()` method taking `Dict[str, Any]` and returning `Dict[str, Any]`
3. Implement `get_capabilities()` returning list of capability descriptions
4. Export from `src/agents/__init__.py`
5. Wire up in CLI as needed
