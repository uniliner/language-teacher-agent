# Building Multi-Agent AI Systems: A Quick-Start Guide

## Learn by Doing: Add Pronunciation to Your Language Agent

**Time Required**: 3-5 hours of implementation
**Learning Focus**: Multi-agent architecture and orchestration patterns
**Goal**: Build two new agents that integrate with your existing system

---

## 🎯 What You'll Learn

In this session, you'll understand:

1. **Multi-Agent Architecture**: How to design specialized agents that collaborate
2. **Agent Orchestration**: How the PedagogicalEngine coordinates which agent responds
3. **State Management**: How agents share state through the Learner model
4. **Strategic Decision Making**: How the system decides WHEN to teach pronunciation
5. **LLM Integration**: How to use Claude for pedagogical decisions

---

## 🏗️ The Architecture: How Agents Work Together

```
User Input
    ↓
PedagogicalEngine (The Orchestrator) ⭐
    ↓
    ├─→ ConversationAgent  (chat with learner)
    ├─→ VocabularyAgent    (teach words)
    ├─→ GrammarAgent        (teach grammar)
    └─→ PronunciationAgent  (teach pronunciation) ← NEW!
```

**Key Insight**: The PedagogicalEngine decides **which agent should respond** based on:
- Conversation flow (is the learner struggling?)
- Learner confidence (don't overwhelm beginners)
- What needs review (spaced repetition)
- Teaching frequency (don't teach pronunciation too often)

---

## 📋 Implementation Plan (3-5 Hours)

### Hour 1: Data Models & Pattern Database

**What you'll build**:
- `PronunciationPattern` model
- Pattern database (JSON) with ~10 German pronunciation patterns

**Why it matters**:
Rich data models enable intelligent behavior. Each field is a capability.

**Tasks**:
```python
# src/models/pronunciation.py
class PronunciationPattern(BaseModel):
    pattern_id: str
    name: str  # e.g., "ICH-Laut (soft ch)"
    category: str  # "vowels", "consonants", etc.
    difficulty: str  # "A1", "A2", etc.

    # Teaching content
    description: str  # "The soft 'ch' sound like in 'ich'"
    examples: List[str]  # ["ich", "mich", "licht", "nicht"]
    teaching_notes: str  # "Touch tongue to roof of mouth..."
    common_mistakes: List[str]  # ["Pronouncing like 'k'"]

    # Progress tracking
    mastery_score: float = 0.0
    practice_count: int = 0
    next_review: Optional[datetime] = None
```

Create `data/pronunciation_patterns.json` with 10 patterns:
- Umlauts (ä, ö, ü)
- ICH-Laut vs ACH-Laut
- EU diphthong
- Final devoicing
- Word stress
- etc.

---

### Hour 2: The PronunciationTeachingAgent

**What you'll build**:
- Complete agent implementation
- Pattern selection logic
- LLM integration for generating explanations

**Key patterns to learn**:

1. **Agent Interface Pattern**:
```python
class PronunciationTeachingAgent(Agent):
    def process(self, input_data: Dict) -> Dict:
        """
        All agents implement this same interface.
        Input: Dict with learner state, context, etc.
        Output: Dict with response, actions, etc.
        """
        # 1. Select pattern to teach
        pattern = self._select_pattern(input_data)

        # 2. Generate teaching content (using LLM)
        content = self._generate_teaching_content(pattern)

        # 3. Update learner progress
        self._update_progress(pattern, input_data['learner'])

        return content
```

2. **Pattern Selection Strategy**:
```python
def _select_pattern(self, input_data: Dict) -> PronunciationPattern:
    """
    WHICH pattern should we teach?

    Priority:
    1. Patterns due for review (spaced repetition)
    2. Patterns in recently encountered words
    3. High-frequency, low-difficulty patterns
    """
    learner = input_data['learner']

    # Check for patterns due for review
    for pattern in learner.pronunciation_patterns.values():
        if pattern.next_review and pattern.next_review <= datetime.now():
            return pattern

    # Select new pattern based on frequency & difficulty
    available_patterns = self._load_patterns()
    return self._score_and_select(available_patterns, learner)
```

3. **LLM Integration for Content Generation**:
```python
def _generate_teaching_content(
    self,
    pattern: PronunciationPattern,
    learner: Learner
) -> Dict:
    """
    Use Claude to generate personalized teaching content.

    Learning: Prompts + Context = Personalized Content
    """
    prompt = f"""
    You are teaching German pronunciation to an {learner.cefr_level} learner.

    Pattern: {pattern.name}
    Description: {pattern.description}
    Examples: {', '.join(pattern.examples)}
    Common Mistakes: {pattern.common_mistakes}

    Teaching Notes: {pattern.teaching_notes}

    Generate a brief, friendly explanation (2-3 sentences) and
    suggest a practice word for the learner to try.
    """

    response = self.llm_client.generate_teaching_response(prompt)

    return {
        'explanation': response['explanation'],
        'practice_word': pattern.examples[0],
        'pattern_id': pattern.pattern_id
    }
```

---

### Hour 3: PedagogicalEngine Integration

**What you'll build**:
- Update PedagogicalEngine to consider pronunciation
- Implement timing logic (when to teach vs. when to let conversation flow)

**Key concept: Agent Orchestration**

```python
# src/pedagogy/engine.py

class PedagogicalEngine:
    def analyze_turn(
        self,
        learner_input: str,
        learner: Learner,
        conversation_state: ConversationState
    ) -> TeachingDecision:
        """
        The brain that decides WHAT happens next.

        This is where multi-agent coordination happens!
        """

        # Existing logic: grammar, vocabulary, conversation flow...
        flow_score = conversation_state.flow_score
        error_rate = self._calculate_error_rate(learner_input)

        # NEW: Check if we should teach pronunciation
        if self._should_teach_pronunciation(learner, conversation_state):
            return TeachingDecision(
                strategy=TeachingStrategy.PRONUNCIATION_TEACHING,
                agent='pronunciation_teaching',
                priority=self._calculate_priority(learner)
            )

        # ... other existing logic ...

    def _should_teach_pronunciation(
        self,
        learner: Learner,
        conversation_state: ConversationState
    ) -> bool:
        """
        Strategic decision: Is NOW a good time to teach pronunciation?

        Consider:
        - Conversation flow (don't interrupt if flow < 0.4)
        - Learner confidence (don't overwhelm if VERY_LOW)
        - Teaching frequency (not too often - every ~15 turns)
        - Pattern availability (are there patterns to teach?)
        """
        # Don't interrupt struggling conversations
        if conversation_state.flow_score < 0.4:
            return False

        # Don't overwhelm low-confidence learners
        if learner.confidence_level == ConfidenceLevel.VERY_LOW:
            return False

        # Don't teach too frequently
        turns_since = self._turns_since_last_pronunciation_teaching(conversation_state)
        if turns_since < 15:
            return False

        # Do we have patterns due for review?
        if self._has_patterns_due_for_review(learner):
            return True

        # Do we have new patterns to introduce?
        if self._has_new_patterns(learner):
            return True

        return False
```

**Learning Moment**: This is **strategic AI decision-making**:
- Multiple factors considered
- Context-sensitive (same action can be good/bad depending on context)
- Prioritization (what's most important right now?)
- Adaptive (changes based on learner state)

---

### Hour 4: CLI Integration & State Management

**What you'll build**:
- Add pronunciation fields to Learner model
- Update CLI to handle pronunciation responses
- Test the complete flow

**State Management Pattern**:

```python
# src/models/learner.py

class Learner(BaseModel):
    # ... existing fields ...

    # NEW: Pronunciation state
    pronunciation_patterns: Dict[str, PronunciationPattern] = {}
    pronunciation_mastery_overall: float = 0.0
```

**CLI Integration**:

```python
# src/cli.py

async def main():
    # ... existing setup ...

    while True:
        user_input = await get_user_input()

        # Process through engine
        decision = pedagogical_engine.analyze_turn(
            user_input, learner, conversation_state
        )

        # Route to appropriate agent
        if decision.strategy == TeachingStrategy.PRONUNCIATION_TEACHING:
            response = pronunciation_teaching_agent.process({
                'learner': learner,
                'conversation_state': conversation_state,
                'decision': decision
            })
            print(f"\n🎤 Pronunciation Tip: {response['explanation']}")
            print(f"Practice word: {response['practice_word']}")

            # Update learner state
            learner.pronunciation_patterns[response['pattern_id']] = ...

        # ... other strategies ...
```

---

### Hour 5: Testing & Refinement

**What you'll do**:
- Test the complete flow
- Adjust teaching frequency
- Fine-tune pattern selection
- Add spaced repetition logic

**Test Scenarios**:
1. New learner encounters umlaut word → system teaches umlaut pattern
2. Learner practiced a pattern → system schedules review
3. Pattern due for review → system triggers practice
4. Conversation flow low → system suppresses pronunciation teaching
5. Low confidence learner → system prioritizes confidence building

---

## 🎓 Key Architecture Patterns You'll Learn

### 1. Agent Pattern
```python
class Agent(ABC):
    @abstractmethod
    def process(self, input_data: Dict) -> Dict:
        """All agents implement this interface"""
```

**Why it matters**: Standardized interface allows plug-and-play agents.

### 2. Orchestrator Pattern
```python
class PedagogicalEngine:
    def analyze_turn(self, ...) -> TeachingDecision:
        """Decides WHICH agent should respond"""
```

**Why it matters**: Centralized coordination enables strategic decision-making.

### 3. Shared State Pattern
```python
learner = Learner(...)  # All agents read/update this
```

**Why it matters**: Agents coordinate through shared state instead of direct coupling.

### 4. Strategy Pattern
```python
TeachingStrategy.PRINT_UNCIATION_TEACHING
```

**Why it matters**: Encapsulates algorithms and makes them interchangeable.

---

## 📁 File Structure

```
src/
├── models/
│   └── pronunciation.py              # NEW - PronunciationPattern model
├── agents/
│   └── pronunciation_teaching.py     # NEW - Teaching agent
├── pedagogy/
│   └── engine.py                     # MODIFY - Add pronunciation decisions
├── models/
│   └── learner.py                    # MODIFY - Add pronunciation fields
└── cli.py                            # MODIFY - Handle pronunciation responses

data/
└── pronunciation_patterns.json       # NEW - Pattern database
```

---

## 🚀 Quick Start Commands

```bash
# Create the model file
touch src/models/pronunciation.py

# Create the agent file
touch src/agents/pronunciation_teaching.py

# Create pattern database
touch data/pronunciation_patterns.json

# Run the application
python -m src
```

---

## 🎯 Success Criteria

You've successfully learned multi-agent architecture when you can:

1. ✅ Explain why multiple agents are better than one giant agent
2. ✅ Describe how the PedagogicalEngine orchestrates agents
3. ✅ Implement a new agent from scratch
4. ✅ Add the agent to the orchestration logic
5. ✅ Share state between agents through the Learner model
6. ✅ Make strategic decisions about when to act

---

## 💡 Pro Tips

1. **Start Simple**: Don't worry about audio assessment yet. Start with text-based teaching.
2. **Test Often**: Run the app after each hour to see your changes working.
3. **Read Existing Code**: Study `src/agents/conversation.py` to understand the pattern.
4. **Experiment**: Try different pattern selection strategies.
5. **Ask Questions**: If you don't understand WHY something is done this way, ask!

---

## 📚 Resources

- **Existing Agent**: [src/agents/conversation.py](../src/agents/conversation.py) - Study this first!
- **Pedagogical Engine**: [src/pedagogy/engine.py](../src/pedagogy/engine.py) - See how it orchestrates
- **Learner Model**: [src/models/learner.py](../src/models/learner.py) - Understand state management
- **Project Overview**: [CLAUDE.md](../CLAUDE.md) - System architecture

---

## 🔧 Dependencies

None! Everything you need is already installed. We'll use:
- Pydantic (for models)
- Anthropic Claude (for LLM)
- Existing infrastructure

---

**Ready to start? Let's build a pronunciation agent together! 🚀**

Start with Hour 1: Create the data model and pattern database. I'll guide you through each step.
