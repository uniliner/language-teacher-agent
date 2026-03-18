# Adaptive Language Learning Companion

An AI-powered language learning agent that adapts to your level, learning style, and progress over time.

## Features

- 🗣️ **Natural conversation practice** in German (extensible to other languages)
- 🧠 **Adaptive learning** - tracks vocabulary, grammar patterns, and confidence
- 📚 **Bottom-up curriculum** - builds personalized learning path from interactions
- ⚖️ **Smart correction** - knows when to correct vs. preserve conversation flow
- 🔄 **Spaced repetition** - autonomously recycles vocabulary and grammar
- 🎯 **Confidence tracking** - adjusts difficulty based on your comfort level

## Architecture (Multi-Agent Design)

```
language-teacher-agent/
├── src/
│   ├── agents/              # Agent implementations
│   │   ├── base.py         # Abstract base agent
│   │   ├── conversation.py # Conversation agent (German)
│   │   └── # Future: pronunciation_agent, grammar_agent, etc.
│   ├── models/             # Data models
│   │   ├── learner.py      # Learner state
│   │   ├── vocabulary.py   # Vocabulary tracking
│   │   └── grammar.py      # Grammar pattern tracking
│   ├── pedagogy/           # Teaching logic
│   │   ├── engine.py       # Pedagogical decision engine
│   │   └── strategies.py   # Teaching strategies
│   ├── memory/             # Persistence
│   │   ├── store.py        # Memory store interface
│   │   └── json_store.py   # JSON implementation
│   ├── llm/                # LLM integration
│   │   ├── client.py       # Claude API client
│   │   └── prompts.py      # Prompt templates
│   └── cli.py              # Command-line interface
├── data/                   # Learner data storage
├── tests/
└── requirements.txt
```

## Getting Started

### Prerequisites
- Python 3.10 or higher
- An Anthropic API key (get one at [console.anthropic.com](https://console.anthropic.com))

### Installation

```bash
# 1. Clone or navigate to the project
cd language-teacher-agent

# 2. Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set your API key
export ANTHROPIC_API_KEY="your-api-key-here"

# Or create a .env file:
cp .env.example .env
# Edit .env and add your API key
```

### Running

```bash
# Run the language teacher
python -m src

# Or use the CLI directly
python src/cli.py

# With a custom data directory
python -m src --data-dir /path/to/data
```

### First Time

1. **Enter your name** - This creates your learner profile
2. **Choose your level** - A1 (beginner) through C2 (advanced)
3. **Start conversing** - The agent will adapt to your level automatically

## Design Philosophy

- **Extensible**: Multi-agent architecture allows adding specialized agents
- **Learner-centered**: Curriculum emerges from the learner, not predefined
- **Flow-aware**: Balances correction with natural conversation
- **Long-term memory**: Tracks progress over weeks and months
