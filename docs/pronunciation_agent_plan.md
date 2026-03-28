# Pronunciation Agent Implementation Plan

## Executive Summary

This document outlines a comprehensive plan to add pronunciation teaching and assessment capabilities to the language-teacher-agent system. The implementation introduces two complementary agents that work strategically to teach pronunciation patterns and assess learner pronunciation quality.

---

## 1. Overview of Goals

### Primary Objectives

1. **Strategic Pronunciation Teaching**: Teach pronunciation in a cumulative, strategic manner rather than attempting to teach every word
2. **Pronunciation Assessment**: Evaluate learner pronunciation quality through audio input
3. **Integration**: Seamlessly integrate with existing pedagogical engine and multi-agent architecture
4. **Progress Tracking**: Track pronunciation learning similar to vocabulary and grammar patterns

### Success Criteria

- Learners demonstrate improved pronunciation of target patterns over time
- Pronunciation teaching doesn't disrupt conversation flow
- System adapts pronunciation difficulty based on learner confidence and performance
- Assessment provides actionable, specific feedback

---

## 2. Agent Architecture

### 2.1 Two-Agent Design

We propose two specialized agents that work in concert:

#### **PronunciationTeachingAgent** (`src/agents/pronunciation_teaching.py`)

**Responsibilities:**
- Decide which pronunciation patterns to teach and when
- Generate pronunciation explanations, examples, and exercises
- Track learner progress on pronunciation patterns
- Integrate with pedagogical engine for timing decisions

**Key Capabilities:**
- Pattern-based pronunciation instruction (e.g., "umlauts", "ch vs. sch", "word-final devoicing")
- IPA (International Phonetic Alphabet) instruction for advanced learners
- Minimal pair exercises for distinguishing similar sounds
- Progressive difficulty scaling from simple sounds to complex words

#### **PronunciationAssessmentAgent** (`src/agents/pronunciation_assessment.py`)

**Responsibilities:**
- Accept audio input from learner (via CLI)
- Transcribe audio using speech recognition
- Compare learner pronunciation against target
- Provide specific, actionable feedback on pronunciation quality

**Key Capabilities:**
- Speech-to-text transcription (using OpenAI Whisper or similar)
- Phoneme-level analysis (using library like phonemizer or montreal-forced-aligner)
- Scoring pronunciation accuracy (0.0-1.0 scale)
- Identifying specific phoneme errors and suggesting corrections

---

## 3. Data Models

### 3.1 PronunciationPattern Model

**File**: `src/models/pronunciation.py`

```python
class PronunciationPattern(BaseModel):
    """A pronunciation pattern or rule that learners master over time."""

    pattern_id: str
    name: str  # e.g., "Umlaut Vowels", "ICH-Laut vs. ACH-Laut"
    category: PronunciationCategory  # VOWELS, CONSONANTS, STRESS, INTONATION
    difficulty: DifficultyLevel  # A1, A2, B1, B2, C1

    # Pattern definition
    description: str  # Human-readable explanation
    examples: List[str]  # Example words demonstrating the pattern
    ipa_representation: Optional[str]  # IPA notation for the pattern
    common_mistakes: List[str]  # Typical errors learners make

    # Teaching materials
    teaching_notes: str  # Detailed explanation for LLM to use
    minimal_pairs: Optional[List[Tuple[str, str]]]  # For contrasting sounds

    # Progress tracking
    mastery_score: float = 0.0  # 0.0 to 1.0
    first_encountered: Optional[datetime] = None
    last_practiced: Optional[datetime] = None
    practice_count: int = 0
    success_count: int = 0

    # Spaced repetition
    next_review: Optional[datetime] = None
    interval_days: int = 1
    easiness_factor: float = 2.5

    class PronunciationCategory(Enum):
        VOWELS = "vowels"
        CONSONANTS = "consonants"
        CONSONANT_CLUSTERS = "consonant_clusters"
        STRESS = "stress"
        INTONATION = "intonation"
        SOUND_CHANGES = "sound_changes"  # e.g., final devoicing
```

### 3.2 PronunciationAttempt Model

```python
class PronunciationAttempt(BaseModel):
    """Record of a learner's pronunciation attempt."""

    attempt_id: str
    pattern_id: str
    target_word: str
    target_ipa: str

    # Audio data
    audio_file_path: Optional[str] = None  # Path to saved audio
    transcription: str  # What the learner said (transcribed)

    # Assessment
    accuracy_score: float  # 0.0 to 1.0
    phoneme_errors: List[PhonemeError]  # Specific phoneme mistakes
    feedback: str  # Human-readable feedback

    # Metadata
    timestamp: datetime
    context: Optional[str] = None  # Sentence or context word appeared in
```

### 3.3 PhonemeError Model

```python
class PhonemeError(BaseModel):
    """A specific phoneme-level pronunciation error."""

    target_phoneme: str  # Expected phoneme (IPA)
    actual_phoneme: str  # What learner said (IPA)
    severity: ErrorSeverity  # MINOR, MODERATE, SEVERE
    position: int  # Position in word
    suggestion: str  # How to correct it
```

---

## 4. Strategic Teaching Logic

### 4.1 What to Teach: Pattern Selection Strategy

**Philosophy**: Teach pronunciation patterns, not individual words. A single pattern (e.g., "umlaut pronunciation") applies to hundreds of words.

**Pattern Database**: Predefined curriculum of ~30-40 German pronunciation patterns, organized by:

1. **Frequency**: How common the pattern is in German
2. **Difficulty**: Relative difficulty for English speakers
3. **Interference**: Sounds that don't exist in English or are very different
4. **Importance**: Impact on comprehensibility if mispronounced

**Priority Categories** (in order):
1. **Vowel quality** (a vs ä, o vs ö, u vs ü)
2. **Critical consonants** (ch vs sch, ü, eu)
3. **Word stress** (compound words, verb prefixes)
4. **Consonant clusters** (schp, scht, kn, pf)
5. **Sound changes** (final devoicing: Tag -> Tak)
6. **Intonation patterns** (questions vs. statements)

### 4.2 When to Teach: Timing Strategy

Integration with `PedagogicalEngine`:

**Introduction Triggers:**
- Every ~15 conversation turns (less frequent than vocabulary/grammar)
- When a word containing a new pattern is encountered for the 3rd time
- When learner confidence is MODERATE or higher (avoid overwhelming low-confidence learners)
- When no major grammar/vocabulary issues need attention

**Practice Triggers:**
- Spaced repetition based on `PronunciationPattern.next_review`
- When learner mispronounces a word containing a known pattern (detected via assessment)
- Every ~20 turns as maintenance

**Suppression Triggers:**
- Conversation flow < 0.4 (prioritize fluency)
- Learner confidence VERY_LOW (build confidence first)
- Error rate > 40% (focus on core issues before pronunciation)

### 4.3 Teaching Strategies

Adapted from `TeachingStrategy` enum, add pronunciation-specific strategies:

```python
class PronunciationTeachingStrategy(Enum):
    """Strategies for teaching pronunciation."""

    # Explanation strategies
    EXPLICIT_INSTRUCTION = "explicit_instruction"  # Direct explanation of mouth position
    ANALOGY = "analogy"  # Compare to similar English sounds
    CONTRASTIVE = "contrastive"  # Compare similar German sounds (minimal pairs)

    # Practice strategies
    LISTEN_REPEAT = "listen_repeat"  # Hear target, repeat it
    MINIMAL_PAIRS = "minimal_pairs"  # Distinguish similar sounds
    CONTEXTUAL_PRACTICE = "contextual_practice"  # Practice in sentences
    TONGUE_TWISTER = "tongue_twister"  # Fun, challenging practice

    # Feedback strategies
    IMMEDIATE_FEEDBACK = "immediate_feedback"  # Correct right after attempt
    DELAYED_FEEDBACK = "delayed_feedback"  Note at end of exercise
    GENTLE_FEEDBACK = "gentle_feedback"  # Soft correction, focus on positives
```

---

## 5. Technology Stack

### 5.1 Speech Recognition

**Option A: OpenAI Whisper API** (Recommended)
- Pros: High accuracy, supports multiple languages, easy API
- Cons: Requires API key, cost (though minimal)
- Use case: Transcribe learner audio for assessment

**Option B: Mozilla DeepSpeech** (Open source alternative)
- Pros: Free, self-hosted, privacy-preserving
- Cons: Lower accuracy on German, requires model download
- Use case: Cost-sensitive or offline scenarios

**Implementation:**
```python
# src/pronunciation/transcriber.py
class AudioTranscriber:
    async def transcribe(audio_file: Path) -> str:
        # Use Whisper API to transcribe audio
        pass
```

### 5.2 Phoneme Analysis

**Option A: Montreal Forced Aligner** (Most accurate)
- Pros: Precise phoneme-level alignment, used in linguistics research
- Cons: Heavy setup, requires acoustic model
- Use case: Detailed assessment when needed

**Option B: phonemizer + Distance Metrics** (Simpler)
- Pros: Lightweight, easy to implement
- Cons: Less precise, no actual audio analysis
- Use case: Quick feedback based on text comparison

**Option C: SpeechSignal API / Similar** (Commercial)
- Pros: Purpose-built for pronunciation assessment
- Cons: Cost, vendor lock-in
- Use case: Production deployment with budget

**Recommended Implementation Path:**
1. **Phase 1**: Use text-based comparison (phonemizer) for MVP
2. **Phase 2**: Integrate actual phoneme alignment (Montreal Forced Aligner)
3. **Phase 3**: Consider commercial APIs for enhanced accuracy

### 5.3 Audio Recording

**CLI Integration:**
```python
# src/pronunciation/audio_recorder.py
class AudioRecorder:
    def record(self, duration: int = 5) -> Path:
        """Record audio from microphone, save to file."""
        # Use pyaudio or sounddevice
        pass
```

**Libraries:**
- `sounddevice`: Cross-platform audio recording
- `pyaudio`: Alternative, more configurable
- `wav`: Built-in Python wav file handling

---

## 6. Integration with Existing System

### 6.1 PedagogicalEngine Integration

Extend `PedagogicalEngine.analyze_turn()` to consider pronunciation:

```python
# In PedagogicalEngine
def analyze_turn(
    self,
    learner_input: str,
    learner: Learner,
    conversation_state: ConversationState,
    # New parameter
    pronunciation_request: Optional[PronunciationRequest] = None,
) -> TeachingDecision:
    """Analyze turn and decide teaching action."""

    # Existing logic for grammar/vocabulary...

    # New: Check if pronunciation teaching is appropriate
    if pronunciation_request and self._should_teach_pronunciation(learner):
        return TeachingDecision(
            strategy=TeachingStrategy.PRONUNCIATION_TEACHING,
            target_pattern=pronunciation_request.pattern_id,
            priority=self._calculate_pronunciation_priority(learner, pronunciation_request),
        )
```

### 6.2 Learner State Extension

Add pronunciation tracking to `Learner` model:

```python
# In src/models/learner.py
class Learner(BaseModel):
    # ... existing fields ...

    # New pronunciation fields
    pronunciation_patterns: Dict[str, PronunciationPattern] = {}
    pronunciation_attempts: List[PronunciationAttempt] = []
    pronunciation_mastery_overall: float = 0.0
```

### 6.3 Conversation Flow Integration

**CLI Enhancement:**
- Add command to trigger pronunciation practice: `/pronounce <word>`
- Add command for pattern practice: `/pronunciation-practice <pattern>`
- Automatically offer pronunciation practice when teaching new patterns

**Example CLI Interaction:**
```
You: Guten Tag, wie geht's?
Agent: [Responds conversationally]

[Later, after introducing umlauts]
Agent: I noticed we're using words with umlauts (ä, ö, ü). Would you like to practice pronouncing them?
You: /pronounce schön
Agent: Let's practice "schön". Say it aloud when ready.
[Recording... 3... 2... 1...]
Agent: Good attempt! Your 'ö' vowel was a bit tense. Try rounding your lips more.
```

---

## 7. Phased Implementation Plan

### Phase 1: Foundation (Week 1-2)
**Goal**: Basic pronunciation teaching without audio assessment

**Tasks:**
1. Create `PronunciationPattern` and `PronunciationAttempt` models
2. Build initial pattern database (15-20 core German patterns)
3. Implement `PronunciationTeachingAgent` with text-based teaching
4. Integrate with `PedagogicalEngine` for timing
5. Add pronunciation fields to `Learner` model
6. Create CLI commands for manual pronunciation practice triggers
7. Implement spaced repetition for pronunciation patterns

**Deliverables:**
- `src/models/pronunciation.py`
- `src/agents/pronunciation_teaching.py`
- Updated `src/models/learner.py`
- Updated `src/pedagogy/engine.py`
- Pattern database JSON file

### Phase 2: Audio Recording (Week 3)
**Goal**: Add audio capture capability

**Tasks:**
1. Implement `AudioRecorder` class
2. Add audio recording to CLI
3. Handle audio file storage (temporary files)
4. Add audio recording triggers in conversation
5. Error handling for microphone access

**Deliverables:**
- `src/pronunciation/audio_recorder.py`
- Updated `src/cli.py`
- Documentation on microphone setup

### Phase 3: Speech Recognition (Week 4)
**Goal**: Transcribe learner audio

**Tasks:**
1. Integrate OpenAI Whisper API (or alternative)
2. Implement `AudioTranscriber` class
3. Handle transcription errors and edge cases
4. Add fallback to text input if microphone unavailable

**Deliverables:**
- `src/pronunciation/transcriber.py`
- Configuration for Whisper API key
- Error handling and retry logic

### Phase 4: Phoneme Analysis (Week 5-6)
**Goal**: Assess pronunciation quality

**Tasks:**
1. Implement text-based phoneme comparison (phonemizer)
2. Create phoneme distance metrics
3. Generate specific feedback based on errors
4. Implement scoring algorithm
5. Track pronunciation attempts

**Deliverables:**
- `src/pronunciation/phoneme_analyzer.py`
- `PronunciationAttempt` model usage
- Feedback generation logic

### Phase 5: Assessment Agent (Week 7-8)
**Goal**: Complete pronunciation assessment workflow

**Tasks:**
1. Implement `PronunciationAssessmentAgent`
2. Integrate assessment results with `PronunciationTeachingAgent`
3. Close the loop: assessment informs next teaching decision
4. Add adaptive difficulty based on performance
5. Implement progress tracking and reporting

**Deliverables:**
- `src/agents/pronunciation_assessment.py`
- Integration tests for full workflow
- Progress metrics and dashboards

### Phase 6: Advanced Features (Week 9-10)
**Goal:**Enhanced teaching capabilities

**Tasks:**
1. Implement minimal pair exercises
2. Add tongue twisters for advanced practice
3. Integrate with Montreal Forced Aligner for precision
4. Add prosody (intonation, stress) assessment
5. Create pronunciation exercises outside of conversation

**Deliverables:**
- Enhanced teaching strategies
- Advanced phoneme alignment
- Exercise modes and templates

### Phase 7: Polish & Testing (Week 11-12)
**Goal**: Production-ready implementation

**Tasks:**
1. Comprehensive testing (unit, integration)
2. User testing with German learners
3. Performance optimization
4. Documentation completion
5. Error handling edge cases

**Deliverables:**
- Test suite with >80% coverage
- User documentation
- API documentation
- Bug fixes and refinements

---

## 8. Pattern Database Schema

### Example German Pronunciation Patterns

```json
{
  "patterns": [
    {
      "pattern_id": "umlaut_a",
      "name": "Long Ä (Umlaut A)",
      "category": "vowels",
      "difficulty": "A2",
      "description": "The long ä sound like in 'schön'",
      "examples": ["schön", "können", "löwen", "möchte"],
      "ipa_representation": "øː",
      "common_mistakes": ["Pronouncing like 'ay' in 'say'", "Too tense"],
      "teaching_notes": "Round lips tightly, say 'ee' while keeping lips rounded",
      "minimal_pairs": [["schön", "schon"], ["können", "kennen"]],
      "frequency": "very_high",
      "importance": "high"
    },
    {
      "pattern_id": "ich_laut",
      "name": "ICH-Laut (palatal fricative)",
      "category": "consonants",
      "difficulty": "A1",
      "description": "The soft 'ch' sound after front vowels",
      "examples": ["ich", "mich", "licht", "nicht"],
      "ipa_representation": "ç",
      "common_mistakes": ["Pronouncing like 'k'", "Too harsh"],
      "teaching_notes": "Touch tongue to roof of mouth, hiss like a cat",
      "minimal_pairs": [["ich", "ig"], ["licht", "liegt"]],
      "frequency": "very_high",
      "importance": "critical"
    },
    {
      "pattern_id": "ach_laut",
      "name": "ACH-Laut (velar fricative)",
      "category": "consonants",
      "difficulty": "A1",
      "description": "The harsh 'ch' sound after back vowels",
      "examples": ["bach", "noch", "machen", "achtsam"],
      "ipa_representation": "x",
      "common_mistakes": ["Pronouncing like 'k'", "Too soft"],
      "teaching_notes": "Constrict throat, make harsh hissing sound like Scottish 'loch'",
      "minimal_pairs": [["bach", "back"], ["noch", "Nacke"]],
      "frequency": "high",
      "importance": "critical"
    },
    {
      "pattern_id": "final_devoicing",
      "name": "Auslautverhärtung (Final Devoicing)",
      "category": "sound_changes",
      "difficulty": "A2",
      "description": "Voiced consonants become voiceless at end of word",
      "examples": [
        ["Tag", "tak"],  // g -> k
        ["Hund", "hʊnt"],  // d -> t
        ["Weg", "vɛk"]  // g -> k
      ],
      "ipa_representation": "Obstruents devoice in coda position",
      "common_mistakes": ["Pronouncing final d as 'd' not 't'"],
      "teaching_notes": "All final b/d/g/v/w/z are pronounced as p/t/k/f/p/s",
      "minimal_pairs": null,
      "frequency": "very_high",
      "importance": "high"
    },
    {
      "pattern_id": "eu_diphthong",
      "name": "EU Diphthong",
      "category": "vowels",
      "difficulty": "A2",
      "description": "The 'oi' sound as in 'Deutsch'",
      "examples": ["Deutsch", "heute", "neun", "Euro"],
      "ipa_representation": "ɔʏ",
      "common_mistakes": ["Pronouncing like 'oo-ee'", "First vowel too open"],
      "teaching_notes": "Start with rounded 'o' sound, glide to tight 'ü'",
      "minimal_pairs": [["heute", "hütte"], ["neun", "nein"]],
      "frequency": "high",
      "importance": "medium"
    }
  ]
}
```

---

## 9. Open Questions & Decisions Needed

### 9.1 Technology Choices

1. **Speech Recognition**: OpenAI Whisper vs. Mozilla DeepSpeech vs. other?
   - Recommendation: Start with Whisper for accuracy, evaluate cost

2. **Phoneme Analysis**: Montreal Forced Aligner vs. text-based vs. commercial API?
   - Recommendation: Text-based for MVP, MFA for Phase 4

3. **Audio Library**: sounddevice vs. pyaudio?
   - Recommendation: sounddevice (simpler API, cross-platform)

### 9.2 Pedagogical Decisions

1. **Teaching Frequency**: How often to introduce pronunciation patterns?
   - Proposal: Every 15-20 turns (configurable)

2. **Pattern Priority**: Order of pattern introduction?
   - Proposal: By frequency × difficulty score (high frequency, low difficulty first)

3. **Assessment Trigger**: When to assess pronunciation?
   - Proposal: Only when learner requests OR when practicing specific patterns

4. **Feedback Detail**: How technical should feedback be?
   - Proposal: Start simple, add IPA for advanced learners (B1+)

### 9.3 User Experience

1. **Audio Recording Opt-in**: Should pronunciation be optional or encouraged?
   - Proposal: Optional by default, encourage when teaching new patterns

2. **CLI Commands**: What commands to expose?
   - Proposal: `/pronounce <word>`, `/pronunciation-practice`, `/pronunciation-status`

3. **Fallback for No Mic**: What if learner has no microphone?
   - Proposal: Skip audio assessment, use self-reporting or text-based practice

---

## 10. Success Metrics

### Quantitative Metrics

- **Pattern Coverage**: Learners master 80% of high-priority patterns within 3 months
- **Accuracy Improvement**: Average pronunciation score improves by 30% after practicing a pattern
- **Engagement**: Learners voluntarily practice pronunciation (not forced)
- **Flow Preservation**: Conversation flow doesn't decrease significantly when teaching pronunciation

### Qualitative Metrics

- Learner feedback on pronunciation teaching helpfulness
- Subjective improvement in confidence speaking German
- Reduced frustration with difficult sounds
- Ability to self-correct pronunciation based on learned patterns

---

## 11. Risks & Mitigation

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Speech recognition fails on German accents | Medium | High | Use German-specific models, allow manual correction |
| Audio recording issues (permissions, hardware) | Medium | Medium | Fallback to text-only mode, clear error messages |
| Phoneme analysis inaccurate | High | High | Combine multiple methods, focus on high-confidence errors |
| API costs (Whisper) high | Low | Medium | Cache transcriptions, use open-source fallback |

### Pedagogical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Teaching overwhelms learners | Medium | High | Conservative introduction rate, flow-aware teaching |
| Incorrect feedback discourages learners | Medium | High | Confidence scoring on feedback, prioritize clear errors |
| Patterns don't transfer to real speech | High | High | Contextual practice, minimal pairs, real-word examples |
| Over-emphasis on perfection | Medium | Medium | Focus on intelligibility over native-like pronunciation |

---

## 12. Next Steps

1. **Review this plan** with stakeholders and gather feedback
2. **Confirm technology choices** (Whisper, phonemizer, etc.)
3. **Decide on Phase 1 scope** - start with text-only or include audio from beginning?
4. **Set up development environment** for audio processing dependencies
5. **Create initial pattern database** with 15-20 core German patterns
6. **Begin implementation** of Phase 1 tasks

---

## Appendix A: File Structure

```
src/
├── agents/
│   ├── pronunciation_teaching.py      # NEW
│   └── pronunciation_assessment.py     # NEW
├── models/
│   └── pronunciation.py                # NEW
├── pedagogy/
│   └── engine.py                       # MODIFY (add pronunciation decisions)
├── pronunciation/                      # NEW directory
│   ├── __init__.py
│   ├── audio_recorder.py               # Audio capture
│   ├── transcriber.py                  # Whisper integration
│   ├── phoneme_analyzer.py             # Phoneme comparison
│   └── patterns.json                   # Pattern database
└── cli.py                              # MODIFY (add pronunciation commands)
```

## Appendix B: Dependencies

```
# New requirements for pronunciation feature
sounddevice>=0.4.6           # Audio recording
numpy>=1.24.0                # Audio processing
openai>=1.0.0                # Whisper API
phonemizer>=3.2.1            # Text-to-phoneme conversion
epitran>=1.0                 # Alternative phonemizer
librosa>=0.10.0              # Audio analysis (for Phase 4+)
torch>=2.0.0                 # For MFA or local models (Phase 4+)
```

---

**Document Version**: 1.0
**Last Updated**: 2026-03-28
**Author**: Language Teacher Agent Team
**Status**: Ready for Review
