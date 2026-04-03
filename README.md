# Adaptive Language Learning Companion

An AI-powered language learning agent that adapts to your level, learning style, and progress over time.

## Features

- 🗣️ **Natural conversation practice** in German (extensible to other languages)
- 🧠 **Adaptive learning** - tracks vocabulary, grammar patterns, and confidence
- 📚 **Bottom-up curriculum** - builds personalized learning path from interactions
- ⚖️ **Smart correction** - knows when to correct vs. preserve conversation flow
- 🔄 **Spaced repetition** - autonomously recycles vocabulary and grammar
- 🎯 **Confidence tracking** - adjusts difficulty based on your comfort level
- 🔊 **Audio pronunciation** - listen to native pronunciation examples (new!)
- 🎤 **Pronunciation assessment** - get instant feedback on your accent (new!)
- 📊 **Pronunciation practice mode** - dedicated practice sessions (new!)

## Architecture (Multi-Agent Design)

```
language-teacher-agent/
├── src/
│   ├── agents/              # Agent implementations
│   │   ├── base.py         # Abstract base agent
│   │   ├── conversation.py # Conversation agent (German)
│   │   └── pronunciation_teaching.py # Pronunciation teaching agent
│   ├── models/             # Data models
│   │   ├── learner.py      # Learner state
│   │   ├── vocabulary.py   # Vocabulary tracking
│   │   ├── grammar.py      # Grammar pattern tracking
│   │   └── pronunciation.py # Pronunciation patterns
│   ├── pedagogy/           # Teaching logic
│   │   ├── engine.py       # Pedagogical decision engine
│   │   └── strategies.py   # Teaching strategies
│   ├── memory/             # Persistence
│   │   ├── store.py        # Memory store interface
│   │   └── json_store.py   # JSON implementation
│   ├── speech/             # Audio features (new!)
│   │   ├── client.py       # Azure Speech Service client
│   │   ├── config.py       # Speech configuration
│   │   └── models.py       # Audio data models
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
- (Optional) Azure Speech Service key for audio features (free tier available)

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

# Optional: Add Azure Speech Service for audio features
# Get free tier at: https://azure.microsoft.com/en-us/services/cognitive-services/speech-service/
# Add to .env:
# AZURE_SPEECH_KEY=your-azure-key-here
# AZURE_SPEECH_REGION=eastus  # or your region
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

## Audio Features (New!)

The language teacher now includes audio pronunciation features powered by Azure Speech Service:

### 🔊 Text-to-Speech
- **Listen to native pronunciation** - Hear correct German pronunciation during lessons
- **Practice examples** - Audio playback for vocabulary and pronunciation patterns
- **Multiple voices** - Natural-sounding German neural voices

### 🎤 Pronunciation Assessment
- **Record your speech** - Practice speaking directly into your microphone
- **Instant feedback** - Get accuracy scores for pronunciation, fluency, and prosody
- **Detailed analysis** - See grades (A-F) and personalized improvement tips

### 📊 Pronunciation Practice Mode
- **Dedicated practice sessions** - Focused pronunciation exercises
- **Pattern selection** - Choose specific sounds to practice
- **Interactive learning** - Listen → Record → Assess → Improve loop

### Enabling Audio Features

1. **Get Azure Speech Service credentials** (free tier available):
   - Go to [Azure Portal](https://portal.azure.com/#view/Microsoft_Azure_ProjectOxford/CognitiveServicesHub/~/SpeechServices)
   - Create a Speech Service resource
   - Copy your key and region from "Keys and Endpoint"

2. **Add credentials to `.env`**:
   ```bash
   AZURE_SPEECH_KEY=your-key-here
   AZURE_SPEECH_REGION=eastus  # or your region
   ```

3. **Validate your setup**:
   ```bash
   python validate_audio_setup.py
   ```

### Using Audio Features

**In conversation mode:**
- When a pronunciation tip appears, audio plays automatically
- Choose to practice your pronunciation with recording
- Get instant feedback on your accent

**Pronunciation practice mode:**
```bash
# Launch dedicated pronunciation practice
python -m src --pronunciation-mode

# Or use experimentation mode for faster triggers
python -m src --experiment --pronunciation-mode
```

**Test audio features:**
```bash
# Run the audio test suite
python test_audio_features.py
```

### Audio Requirements

- **Microphone** - For recording your pronunciation
- **Speakers/headphones** - For listening to examples
- **Internet connection** - Azure Speech Service requires internet access

### Troubleshooting Audio

| Issue | Solution |
|-------|----------|
| "Audio features disabled" | Add AZURE_SPEECH_KEY and AZURE_SPEECH_REGION to `.env` |
| "Could not initialize audio" | Check your microphone and speakers are connected |
| "Assessment failed" | Speak clearly, reduce background noise, check internet |
| No audio playback | Ensure system audio is not muted |

## Design Philosophy

- **Extensible**: Multi-agent architecture allows adding specialized agents
- **Learner-centered**: Curriculum emerges from the learner, not predefined
- **Flow-aware**: Balances correction with natural conversation
- **Long-term memory**: Tracks progress over weeks and months
