# LRU Cache - Comprehensive Explanation

## What is LRU Cache?

**LRU** = **Least Recently Used**

A caching strategy where:
- When cache is FULL, evict the item that hasn't been accessed in the longest time
- Every access (get/put) updates the "recency" of that item
- Assumes **temporal locality**: recently used items are likely to be used again

## Visual Example

### Scenario: Cache size = 3

```
Operation Sequence: ADD A, ADD B, ADD C, GET B, ADD D

Step 1: ADD A
┌────────────────────────────────────────┐
│ Cache: [A]                             │
│ Order: A (most recent)                 │
└────────────────────────────────────────┘

Step 2: ADD B
┌────────────────────────────────────────┐
│ Cache: [A, B]                          │
│ Order: B → A (B most recent)           │
└────────────────────────────────────────┘

Step 3: ADD C
┌────────────────────────────────────────┐
│ Cache: [A, B, C]                       │
│ Order: C → B → A                       │
│ (cache is now FULL)                    │
└────────────────────────────────────────┘

Step 4: GET B (access B, move to front)
┌────────────────────────────────────────┐
│ Cache: [A, B, C]                       │
│ Order: B → C → A                       │
│ (B accessed, moved to front)           │
└────────────────────────────────────────┘

Step 5: ADD D (cache full, evict least recent: A)
┌────────────────────────────────────────┐
│ Cache: [B, C, D]                       │
│ Order: D → B → C                       │
│ (A was evicted - least recent)         │
└────────────────────────────────────────┘
```

## Why LRU Works Well

### Temporal Locality Principle
**If you used something recently, you'll likely use it again soon.**

Real-world examples:
- **Web browser**: You visit same sites repeatedly (news, email, social media)
- **File system**: You access same files repeatedly (project files, configs)
- **CPU cache**: Programs access same memory locations repeatedly (loops)

### In Language Learning Context
```
Learner discusses topics in patterns:

Session 1: "food", "family", "daily routine"
Session 2: "food", "hobbies", "food"  ← food repeated
Session 3: "daily routine", "food", "work"  ← food, daily routine repeated

LRU keeps "food" in cache because it's accessed frequently
LRU evicts "work" if cache gets full (least recently used)
```

## Python's `lru_cache` Decorator

### Basic Usage
```python
from functools import lru_cache
import time

@lru_cache(maxsize=128)
def expensive_function(n):
    """Simulate expensive calculation."""
    print(f"Calculating {n}...")
    time.sleep(1)  # Simulate work
    return n * n

# First call: takes 1 second
result1 = expensive_function(5)
# Output: Calculating 5...
# (1 second delay)

# Second call: instant (cached!)
result2 = expensive_function(5)
# Output: (no "Calculating" message - instant return)

# Check cache statistics
print(expensive_function.cache_info())
# CacheInfo(hits=1, misses=1, maxsize=128, currsize=1)
```

### Parameters
```python
@lru_cache(maxsize=128)  # Maximum 128 cached entries
@lru_cache(maxsize=None) # Unlimited cache (careful!)
@lru_cache(maxsize=32)   # Small cache for memory-constrained apps
```

### Cache Statistics
```python
cache_info()  # Returns CacheInfo(hits, misses, maxsize, currsize)

# Example:
# hits=50       # Cached results reused 50 times
# misses=10     # Had to calculate 10 times
# maxsize=128   # Cache can hold 128 items max
# currsize=10   # Currently holding 10 items

# Calculate hit rate
hit_rate = hits / (hits + misses)  # 83% in this example
```

### Clear Cache
```python
expensive_function.cache_clear()  # Remove all cached entries
```

## Implementation: Thread-Safe LRU Cache

The plan mentions using `functools.lru_cache` with `threading.Lock` for concurrency:

```python
from functools import lru_cache
import threading

class ThreadSafeGrammarCache:
    """
    Thread-safe LRU cache for topic→grammar mapping.

    Addresses the concurrency warning in GrammarCurriculumAgent.
    """

    def __init__(self, maxsize=128):
        self.maxsize = maxsize
        self.lock = threading.Lock()
        self._cache = {}

    def get(self, topic: str) -> list:
        """Get grammar patterns for topic (thread-safe)."""
        with self.lock:  # Acquire lock before access
            return self._cache.get(topic, [])

    def set(self, topic: str, patterns: list) -> None:
        """Set grammar patterns for topic (thread-safe)."""
        with self.lock:  # Acquire lock before write
            # LRU eviction logic
            if len(self._cache) >= self.maxsize:
                # Remove least recent entry
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]

            self._cache[topic] = patterns

    def get_or_compute(self, topic: str, compute_fn) -> list:
        """
        Get from cache or compute if missing (thread-safe).

        This is the pattern that would be used with LLM calls.
        """
        # Try to get from cache first
        with self.lock:
            if topic in self._cache:
                return self._cache[topic]

        # Not in cache - compute (outside lock to avoid blocking)
        patterns = compute_fn(topic)

        # Store in cache (with lock)
        with self.lock:
            self._cache[topic] = patterns

        return patterns
```

## Why LRU is Mentioned in the Plan

### The Problem: Class Variable Not Thread-Safe

```python
class GrammarCurriculumAgent:
    # ⚠️ CONCURRENCY RISK
    _topic_grammar_cache: ClassVar[Dict[str, List[str]]] = {
        "food": ["accusative_case", "indefinite_articles"],
        # ...
    }
```

**Why is this a problem?**

```
Thread 1 (User A):                    Thread 2 (User B):
topic = "food"                        topic = "directions"
                                      ↓
Reading from cache...                Reading from cache...
cache["food"]                         cache["directions"]
                                      ↓
Writing to cache...                   Writing to cache...
cache["food"] = [...]                cache["directions"] = [...]
                                      ↓
Race condition! Both threads         ⚠️ CORRUPTION
modifying shared dictionary
simultaneously
```

### The Solution: LRU Cache with Thread Safety

```python
from functools import lru_cache
import threading

class GrammarCurriculumAgent:
    # ✅ THREAD-SAFE LRU Cache
    _cache_lock = threading.Lock()
    _topic_grammar_cache: ClassVar[Dict] = {}

    @classmethod
    @lru_cache(maxsize=128)
    def get_grammar_for_topic(cls, topic: str) -> List[str]:
        """Thread-safe LRU cached lookup."""
        with cls._cache_lock:
            return cls._topic_grammar_cache.get(topic, [])
```

## Comparison: Different Caching Strategies

### LRU vs FIFO vs LFU

```
Strategy: What to evict when cache is full?

LRU (Least Recently Used):
  Evict: Item not accessed in longest time
  Example: Browser cache
  Best: When recent access predicts future access

FIFO (First In First Out):
  Evict: Oldest item (by insertion time)
  Example: Print queue
  Best: When access order doesn't matter

LFU (Least Frequently Used):
  Evict: Item with fewest total accesses
  Example: Database query cache
  Best: When frequency predicts future access

Random:
  Evict: Random item
  Example: Some CPU caches
  Best: Simple, good enough for some cases
```

### Example Scenario

```
Cache operations:
1. ADD A
2. ADD B
3. ADD C
4. GET B (access B)
5. GET B (access B again)
6. ADD D (cache full, evict something)

LRU evicts: A (least recently accessed)
FIFO evicts: A (first in)
LFU evicts: C (least frequently accessed - only once)
Random evicts: any of A, B, C
```

## When to Use LRU Cache

### ✅ Good Use Cases
- Web page content (same pages visited repeatedly)
- Database query results (same queries run repeatedly)
- API responses (same API calls made repeatedly)
- Expensive calculations (fibonacci, matrix operations)
- **Grammar topic mappings** (learners discuss same topics repeatedly)

### ❌ Bad Use Cases
- Sequential access (never repeat items)
- Large single-use items (can't fit in cache)
- Real-time data (cache becomes stale quickly)
- Very small datasets (overhead not worth it)

## Performance Comparison

### Without Cache
```python
def get_grammar_for_topic(topic: str) -> List[str]:
    """Every call requires LLM lookup."""
    response = llm_client.generate_response(
        f"What grammar patterns for topic: {topic}?"
    )
    return parse_patterns(response)

# Performance:
# - Speed: ~500ms per call (LLM latency)
# - Cost: ~$0.0015 per call
# - 1000 calls = $1.50, 500 seconds
```

### With LRU Cache
```python
@lru_cache(maxsize=128)
def get_grammar_for_topic(topic: str) -> List[str]:
    """First call uses LLM, subsequent calls are cached."""
    response = llm_client.generate_response(
        f"What grammar patterns for topic: {topic}?"
    )
    return parse_patterns(response)

# Performance (with 90% cache hit rate):
# - Speed: ~50ms per call (avg: 0.9*1ms + 0.1*500ms)
# - Cost: ~$0.00015 per call (avg: 0.9*$0 + 0.1*$0.0015)
# - 1000 calls = $0.15, 50 seconds (10x faster, 10x cheaper!)
```

## Key Takeaways

1. **LRU** = Evict least recently used items when cache is full
2. **Works well** when recent access predicts future access (temporal locality)
3. **Python provides** `@lru_cache` decorator for easy implementation
4. **Thread safety** requires additional locks for concurrent access
5. **Performance gains**: 10-100x speedup for repeated operations
6. **Memory tradeoff**: Caching uses more RAM to save CPU/time

In the context of GrammarCurriculumAgent, LRU cache would:
- ✅ Speed up topic→grammar lookups
- ✅ Reduce LLM API costs
- ✅ Enable thread-safe concurrent access
- ✅ Automatically manage cache size (evict unused topics)
- ✅ Improve overall system performance
