# Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Interface                           │
│                      (src/cli.py)                               │
└──────────────────────────────────┬──────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Conversation Agent                         │
│                   (src/agents/conversation.py)                  │
│  • Conducts conversations in target language                    │
│  • Analyzes learner input                                       │
│  • Coordinates with pedagogical engine                          │
└─────┬───────────────────────────────┬───────────────────────────┘
      │                               │
      ▼                               ▼
┌──────────────────┐         ┌──────────────────────────────────┐
│   LLM Client     │         │   Pedagogical Engine             │
│ (src/llm/)       │         │  (src/pedagogy/engine.py)        │
│                  │         │                                  │
│ • Claude API     │         │ • Analyze learner state          │
│ • Error detect   │         │ • Make teaching decisions        │
│ • Generate resp  │         │ • Track conversation flow        │
└──────────────────┘         └──────┬───────────────────────────┘
                                     │
                                     ▼
                           ┌─────────────────────┐
                           │   Strategy Selector │
                           │(src/pedagogy/       │
                           │  strategies.py)     │
                           │                     │
                           │ • When to correct   │
                           │ • When to introduce │
                           │ • When to review    │
                           └─────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                         Learner State                            │
│                       (src/models/learner.py)                    │
│                                                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Vocabulary    │  │     Grammar     │  │   Confidence    │ │
│  │   (vocabulary.py)│  │   (grammar.py)  │  │                 │ │
│  │                 │  │                 │  │                 │ │
│  │ • Words/phrases │  │ • Patterns      │  │ • Level tracking│ │
│  │ • Mastery level │  │ • Error rate    │  │ • Adjustment    │ │
│  │ • Spaced rep    │  │ • Weaknesses    │  │                 │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────┬────────────────────────────┘
                                      │
                                      ▼
                            ┌──────────────────┐
                            │  Memory Store    │
                            │ (src/memory/)    │
                            │                  │
                            │ • JSON backend   │
                            │ • Auto-save      │
                            │ • Load/restore   │
                            └──────────────────┘
```

## Data Flow

### Conversation Turn
```
1. User Input → CLI
2. CLI → Agent.process()
3. Agent → LLM Client.analyze_input() (detect errors, vocabulary)
4. Agent → PedagogicalEngine.analyze_turn() (decide what to do)
5. Engine → StrategySelector (choose correction/introduction/continue)
6. Agent → LLM Client.generate_teaching_response() (create response)
7. Agent → Update learner state (vocabulary, grammar, confidence)
8. Response → CLI → User
9. Memory Store.save_learner() (persist state)
```

## Multi-Agent Design (Extensible)

```
Agent (base class)
│
├── ConversationAgent (current)
│   └── Natural conversation practice
│
├── PronunciationAgent (future)
│   └── Accent and pronunciation coaching
│
├── GrammarAgent (future)
│   └── Focused grammar exercises
│
└── VocabularyAgent (future)
    └── Spaced repetition drills
```

## Key Design Decisions

1. **Bottom-Up Curriculum**: No pre-set lessons. Content emerges from conversation.

2. **Flow-Aware**: Pedagogical engine tracks conversation flow and adjusts corrections.

3. **Multi-Agent Architecture**: Easy to add specialized agents without rewriting core.

4. **Pluggable Storage**: JSONStore now, but interface supports SQL, Redis, etc.

5. **Confidence Tracking**: Monitors learner confidence and adjusts difficulty.

6. **Spaced Repetition**: Built-in SM-2 algorithm for vocabulary scheduling.
