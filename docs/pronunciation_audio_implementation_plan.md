# Audio-Enabled Pronunciation Agent Implementation Plan

## Context

The pronunciation teaching agent currently teaches pronunciation patterns using text-based explanations, but lacks audio capabilities for demonstrating correct pronunciation or evaluating learner attempts. This upgrade adds:

1. **Text-to-Speech**: Play German pronunciation examples using Azure Speech Service
2. **Speech Recording**: Record learner's pronunciation attempts via microphone
3. **Pronunciation Assessment**: Evaluate learner pronunciation using Azure's pronunciation assessment API

This enhancement will make the pronunciation teaching more effective by providing audio demonstrations and personalized feedback on the learner's accent and accuracy.

## Architecture Overview

### Recommended Approach: Service-Oriented Architecture

Create a new `src/speech/` module that encapsulates all audio functionality. This follows the existing pattern of separate modules for different concerns (`llm/`, `memory/`, `pedagogy/`).

```
src/speech/
├── __init__.py              # Public API exports
├── config.py                # SpeechConfig, load_speech_config() from env
├── models.py                # PronunciationAssessmentResult, AudioRecording data models
├── client.py                # AzureSpeechClient (main interface)
├── synthesizer.py           # Text-to-Speech functionality
└── recognizer.py            # Speech Recording & Assessment
```

### Key Design Decisions

1. **Separation of Concerns**: Audio logic isolated in speech service, agent focuses on teaching
2. **Backward Compatibility**: All audio features are optional; falls back to text-only if unavailable
3. **Error Resilience**: Comprehensive error handling for missing devices, API failures, etc.
4. **User Experience**: Rich CLI integration with progress bars and visual feedback
5. **Data Privacy**: Recordings are temporary by default; persistent storage opt-in

## Implementation Steps

### Phase 1: Foundation (Days 1-2)

#### Step 1.1: Create Speech Config Module
**File**: `src/speech/config.py`

```python
from dataclasses import dataclass
from typing import Optional
import os
from dotenv import load_dotenv

@dataclass
class SpeechConfig:
    """Configuration for Azure Speech Service."""
    speech_key: str
    speech_region: str
    voice_name: str = "de-DE-KatjaNeural"  # German female voice
    enable_cache: bool = True
    cache_dir: str = "data/audio_cache"

    @classmethod
    def from_env(cls) -> Optional['SpeechConfig']:
        """Load configuration from environment variables."""
        load_dotenv()
        key = os.getenv("AZURE_SPEECH_KEY") or os.getenv("SPEECH_KEY")
        region = os.getenv("AZURE_SPEECH_REGION") or os.getenv("SPEECH_REGION")

        if not key or not region:
            return None
        return cls(speech_key=key, speech_region=region)
```

#### Step 1.2: Create Speech Models
**File**: `src/speech/models.py`

```python
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class AudioRecording:
    """Represents a recorded audio clip."""
    audio_data: bytes
    duration_ms: int
    timestamp: datetime
    pattern_id: Optional[str] = None
    target_text: Optional[str] = None

@dataclass
class PronunciationAssessmentResult:
    """Results from pronunciation assessment."""
    accuracy_score: float  # 0.0 to 1.0
    fluency_score: float
    completeness_score: float
    prosody_score: float
    error_text: Optional[str] = None
    feedback: str = ""  # Human-readable feedback
```

#### Step 1.3: Create Azure Speech Client
**File**: `src/speech/client.py`

Main interface for all speech operations. Wraps Azure Speech SDK with error handling.

```python
class AzureSpeechClient:
    """Main client for Azure Speech Service operations."""

    def __init__(self, config: SpeechConfig):
        self.config = config
        self._init_azure_sdk()

    def synthesize_speech(self, text: str, language: str = "de-DE") -> bytes:
        """Synthesize speech from text and return audio bytes."""

    def record_speech(self, timeout_seconds: int = 5) -> AudioRecording:
        """Record speech from microphone."""

    def assess_pronunciation(self, recording: AudioRecording, target_text: str) -> PronunciationAssessmentResult:
        """Assess pronunciation accuracy against target text."""

    def play_audio(self, audio_data: bytes) -> None:
        """Play audio through default output device."""
```

### Phase 2: Text-to-Speech (Days 3-4)

#### Step 2.1: Implement Speech Synthesizer
**File**: `src/speech/synthesizer.py`

Features:
- Synthesize German text using Azure Neural TTS voices
- Cache synthesized audio to reduce API calls
- Support multiple German voices (male/female options)
- Handle SSML for prosody control

Implementation details:
- Use `azure.cognitiveservices.speech.SpeechSynthesizer`
- Implement file-based caching using hash of input text
- Return audio bytes for playback or storage

#### Step 2.2: Integrate TTS into PronunciationTeachingAgent
**File**: `src/agents/pronunciation_teaching.py`

Enhancement to existing `_generate_teaching_content()` method:

```python
def _generate_teaching_content(self, pattern, learner, conversation_state):
    # ... existing logic ...

    # NEW: Add synthesized audio for practice word
    if self.speech_client:
        audio = self.speech_client.synthesize_speech(
            text=practice_word,
            language="de-DE"
        )
        teaching_content["audio_data"] = audio

    return teaching_content
```

#### Step 2.3: Add Audio Playback to CLI
**File**: `src/cli.py`

Add audio playback to pronunciation tip display:

```python
if pronunciation_result.get("audio_data"):
    # Play pronunciation example
    self.speech_client.play_audio(pronunciation_result["audio_data"])
    self.console.print("   🔊 Played pronunciation example")
```

### Phase 3: Recording & Assessment (Days 5-7)

#### Step 3.1: Implement Speech Recognizer
**File**: `src/speech/recognizer.py`

Features:
- Record from microphone with visual progress indicator
- Use Azure Speech Recognition for transcription
- Integrate Azure Pronunciation Assessment API
- Generate detailed feedback from scores

```python
def record_with_progress(timeout_seconds: int = 5) -> AudioRecording:
    """Record speech with visual progress bar in CLI."""

def assess_pronunciation(recording: AudioRecording, target_text: str) -> PronunciationAssessmentResult:
    """Use Azure's pronunciation assessment to score accuracy."""
```

#### Step 3.2: Add Recording Workflow to CLI
**File**: `src/cli.py`

Add interactive recording prompt after pronunciation tip:

```python
# After showing pronunciation tip
if self.speech_client:
    # Prompt user to practice
    if self._prompt_yes_no("\n🎤 Would you like to practice your pronunciation?"):
        recording = self._record_pronunciation(practice_word)
        assessment = self.speech_client.assess_pronunciation(recording, practice_word)
        self._display_assessment_feedback(assessment)
```

#### Step 3.3: Update Learner Model with Pronunciation Attempts
**File**: `src/models/learner.py`

Extend learner state to track pronunciation assessments:

```python
class Learner(BaseModel):
    # ... existing fields ...
    pronunciation_attempts: List[PronunciationAttempt] = []

class PronunciationAttempt(BaseModel):
    pattern_id: str
    target_word: str
    accuracy_score: float
    timestamp: datetime
```

#### Step 3.4: Link Assessment to Spaced Repetition
**File**: `src/agents/pronunciation_teaching.py`

Update mastery scores based on assessment results:

```python
def _update_learner_progress(learner, pattern, teaching_content, assessment_result=None):
    # ... existing logic ...

    if assessment_result:
        # Update mastery based on pronunciation accuracy
        learner_pattern.update_mastery_from_assessment(
            accuracy_score=assessment_result.accuracy_score
        )
```

### Phase 4: Polish & Testing (Days 8-10)

#### Step 4.1: Add Comprehensive Error Handling

All speech operations should handle:
- `RuntimeError`: No audio device available
- `ConnectionError`: Azure API unreachable
- `PermissionError`: Microphone access denied
- `TimeoutError`: Recording timeout
- `ValueError`: Invalid input parameters

Graceful degradation pattern:
```python
try:
    audio = self.speech_client.synthesize_speech(text)
except (RuntimeError, ConnectionError) as e:
    logger.warning(f"Audio unavailable: {e}")
    # Fall back to text-only mode
    return None
```

#### Step 4.2: Add Audio Cache Management

Implement cache cleanup to prevent disk bloat:
- Remove cache entries older than 30 days
- Limit cache size to 100MB
- Provide CLI command to clear cache

#### Step 4.3: Create Comprehensive Tests

**Unit Tests** (`tests/speech/`):
- Test config loading with/without env vars
- Test audio model serialization
- Mock Azure SDK for testing client methods

**Integration Tests**:
- Test TTS with actual Azure API (use CI credentials)
- Test recording/playback cycle (requires audio device)

**CLI Tests**:
- Test audio prompts and user interaction flows
- Test error scenarios (no device, API failure)

#### Step 4.4: Update Documentation

Update README.md with:
- Audio feature overview
- Environment setup instructions (Azure credentials)
- Troubleshooting common audio issues

## Critical Files to Modify

### New Files to Create

1. **`src/speech/__init__.py`** - Module exports
2. **`src/speech/config.py`** - Configuration management
3. **`src/speech/models.py`** - Audio data models
4. **`src/speech/client.py`** - Main Azure Speech client
5. **`src/speech/synthesizer.py`** - Text-to-speech implementation
6. **`src/speech/recognizer.py`** - Recording and assessment
7. **`tests/speech/test_client.py`** - Unit tests
8. **`tests/speech/test_synthesizer.py`** - TTS tests

### Existing Files to Modify

1. **`src/agents/pronunciation_teaching.py`** - Integrate audio into teaching flow
2. **`src/cli.py`** - Add audio controls and prompts
3. **`src/models/learner.py`** - Track pronunciation attempts
4. **`requirements.txt`** - Add any new dependencies (sounddevice, scipy)
5. **`.env.example`** - Already updated with AZURE_SPEECH_KEY/REGION
6. **`README.md`** - Document audio features

## Testing Strategy

### Local Development Testing

1. **Validate environment**:
   ```bash
   python validate_audio_setup.py
   ```

2. **Test TTS in isolation**:
   ```python
   from src.speech import AzureSpeechClient
   client = AzureSpeechClient.from_env()
   audio = client.synthesize_speech("Guten Tag")
   client.play_audio(audio)
   ```

3. **Test recording**:
   ```python
   recording = client.record_speech(timeout_seconds=5)
   ```

4. **Test assessment**:
   ```python
   result = client.assess_pronunciation(recording, "ich")
   print(f"Accuracy: {result.accuracy_score:.2%}")
   ```

### End-to-End Testing

Run the full conversation flow and trigger pronunciation teaching:
1. Start the app: `python -m src`
2. Conduct conversation in German
3. When pronunciation tip appears, try the audio features
4. Verify playback, recording, and assessment work

### Error Scenario Testing

Test graceful degradation:
1. Run without AZURE_SPEECH_KEY → should fall back to text-only
2. Run in headless environment → should skip audio features
3. Test with network disabled → should handle API failures gracefully

## Edge Cases & Error Handling

### Hardware Issues

| Scenario | Behavior |
|----------|----------|
| No microphone | Skip recording, show helpful message |
| No speakers | Skip playback, show warning |
| Multiple audio devices | Use default, allow configuration |

### API Issues

| Scenario | Behavior |
|----------|----------|
| Azure API down | Fall back to text-only mode |
| Rate limit exceeded | Queue requests or skip TTS |
| Invalid API key | Show setup error message |
| Network timeout | Retry 3x with exponential backoff |

### User Experience Issues

| Scenario | Behavior |
|----------|----------|
| Background noise | Show tip to reduce noise, retry |
| Too quiet/loud | Show feedback on volume levels |
| Wrong language | Detect and suggest language switch |
| Poor pronunciation | Show specific feedback on what to improve |

## Verification Checklist

After implementation, verify:

- [ ] TTS plays German audio clearly
- [ ] Recording captures speech with visual feedback
- [ ] Assessment provides accurate scores
- [ ] CLI integration is smooth and intuitive
- [ ] Fallback to text-only works when audio unavailable
- [ ] All tests pass (unit + integration)
- [ ] No breaking changes to existing functionality
- [ ] Documentation updated
- [ ] Error handling tested for all failure modes

## Bonus Features

### Test/Experimentation Mode

Add a `--pronunciation-mode` flag to the CLI that launches a dedicated pronunciation practice mode:

```bash
python -m src --pronunciation-mode
```

**Features**:
- Interactive pronunciation challenge menu
- Select specific patterns to practice
- Unlimited recording attempts
- Real-time assessment feedback
- Score tracking and improvement metrics
- Bypass conversation flow for focused practice

**Implementation**: New `src/cli.py` command `run_pronunciation_mode()` that:
1. Loads all available pronunciation patterns
2. Displays interactive menu for pattern selection
3. Loop: Play example → Record → Assess → Show feedback → Retry
4. Track scores across attempts
5. Allow exiting back to main conversation

## Summary

This plan adds comprehensive audio capabilities to the pronunciation teaching agent while maintaining backward compatibility and following existing architectural patterns. The service-oriented design ensures clean separation of concerns and makes the code testable and maintainable.

The implementation progresses from foundation → TTS → recording/assessment → polish, with each phase building on the previous one. By the end of Day 10, learners will be able to hear German pronunciation examples, record their own attempts, and receive personalized feedback on their accuracy.
