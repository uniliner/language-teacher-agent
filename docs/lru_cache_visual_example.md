# LRU Cache: Visual Example with Grammar Topics

## Scenario: Cache Size = 5 Topics

### Step-by-Step Evolution

```
═══════════════════════════════════════════════════════════════
INITIAL STATE: Empty cache
═══════════════════════════════════════════════════════════════
Cache: [ ]
Size: 0/5

═══════════════════════════════════════════════════════════════
OPERATION 1: ADD "food"
═══════════════════════════════════════════════════════════════
Cache: [food]
Order: food →
Size: 1/5

Most recent: food
Least recent: food

═══════════════════════════════════════════════════════════════
OPERATION 2: ADD "directions"
═══════════════════════════════════════════════════════════════
Cache: [food, directions]
Order: directions → food →
Size: 2/5

Most recent: directions
Least recent: food

═══════════════════════════════════════════════════════════════
OPERATION 3: ADD "daily routine"
═══════════════════════════════════════════════════════════════
Cache: [food, directions, daily routine]
Order: daily routine → directions → food →
Size: 3/5

═══════════════════════════════════════════════════════════════
OPERATION 4: ADD "family"
═══════════════════════════════════════════════════════════════
Cache: [food, directions, daily routine, family]
Order: family → daily routine → directions → food →
Size: 4/5

═══════════════════════════════════════════════════════════════
OPERATION 5: ADD "past events"
═══════════════════════════════════════════════════════════════
Cache: [food, directions, daily routine, family, past events]
Order: past events → family → daily routine → directions → food →
Size: 5/5 ⚠️ CACHE IS NOW FULL!

═══════════════════════════════════════════════════════════════
OPERATION 6: GET "directions" (access existing item)
═══════════════════════════════════════════════════════════════
Cache: [food, directions, daily routine, family, past events]
Order: directions → past events → family → daily routine → food →
Size: 5/5

⚠️ "directions" moved to front (most recent)!
"food" is now least recent (next to be evicted)

═══════════════════════════════════════════════════════════════
OPERATION 7: ADD "future plans" (cache FULL, evict least recent)
═══════════════════════════════════════════════════════════════
Before: [food, directions, daily routine, family, past events]
        ↑ least recent - EVICT THIS!

After:  [directions, daily routine, family, past events, future plans]
Order: future plans → past events → family → daily routine → directions →
Size: 5/5

✓ "food" was evicted (least recently used)
✓ "future plans" added to front
```

## Real Learning Session Example

```
═══════════════════════════════════════════════════════════════
LEARNER SESSION: 60-minute conversation
═══════════════════════════════════════════════════════════════

Turn 1: Topic = "greetings"
  Cache: [greetings]
  LLM Call: YES (first time)
  Grammar: ["present_tense_regular", "definite_articles_nominative"]

Turn 5: Topic = "food"
  Cache: [greetings, food]
  LLM Call: YES (first time)
  Grammar: ["accusative_case", "indefinite_articles_nominative"]

Turn 8: Topic = "food" (again)
  Cache: [greetings, food]
  LLM Call: NO (cached!) ✅
  Grammar: ["accusative_case", "indefinite_articles_nominative"]
  Speed: <1ms instead of 500ms

Turn 12: Topic = "family"
  Cache: [greetings, food, family]
  LLM Call: YES
  Grammar: ["definite_articles_nominative", "possessive_articles"]

Turn 18: Topic = "food" (third time)
  Cache: [greetings, food, family]
  LLM Call: NO (cached!) ✅
  Speed: <1ms

Turn 25: Topic = "directions"
  Cache: [greetings, food, family, directions]
  LLM Call: YES

Turn 32: Topic = "food" (fourth time)
  Cache: [greetings, food, family, directions]
  LLM Call: NO (cached!) ✅

Turn 45: Topic = "daily routine"
  Cache: [greetings, food, family, directions, daily routine]
  LLM Call: YES

Turn 50: Topic = "hobbies"
  Cache: [greetings, food, family, directions, daily routine] (FULL!)
  LLM Call: YES
  Cache: [food, family, directions, daily routine, hobbies]
  ⚠️ "greetings" evicted (least recent)

Turn 55: Topic = "food" (fifth time)
  Cache: [food, family, directions, daily routine, hobbies]
  LLM Call: NO (cached!) ✅

═══════════════════════════════════════════════════════════════
SESSION STATISTICS
═══════════════════════════════════════════════════════════════
Total topic lookups: 10
Cache hits: 3 (30%)
Cache misses: 7 (70%)
LLM calls saved: 3
Time saved: 3 × 500ms = 1.5 seconds
Cost saved: 3 × $0.0015 = $0.0045

Most popular topic: "food" (accessed 4 times)
Least popular topic: "greetings" (accessed 1 time, evicted)
```

## Performance Comparison: Different Cache Sizes

```
═══════════════════════════════════════════════════════════════
SCENARIO: 1000 turns, 50 unique topics, topic repetition pattern
═══════════════════════════════════════════════════════════════

NO CACHE:
├─ LLM calls: 1000
├─ Time: 500 seconds
└─ Cost: $1.50

CACHE SIZE = 10:
├─ LLM calls: 150 (15% hit rate)
├─ Time: 75 seconds
└─ Cost: $0.23
└─ Memory: ~10KB

CACHE SIZE = 50:
├─ LLM calls: 20 (98% hit rate!)
├─ Time: 10 seconds
└─ Cost: $0.03
└─ Memory: ~50KB

CACHE SIZE = 100:
├─ LLM calls: 5 (99.5% hit rate!)
├─ Time: 2.5 seconds
└─ Cost: $0.0075
└─ Memory: ~100KB

✓ LARGER CACHE = Better performance (but more memory)
✓ DIMINISHING RETURNS: 50→100 only saves $0.02
```

## Thread Safety Visualization

```
═══════════════════════════════════════════════════════════════
WITHOUT THREAD SAFETY: Race Condition
═══════════════════════════════════════════════════════════════

Thread A (User 1):        Thread B (User 2):
topic = "food"            topic = "directions"
    ↓                         ↓
Reading cache...        Reading cache...
cache["food"] = [...]    cache["directions"] = [...]
    ↓                         ↓
Writing to cache...     Writing to cache...
cache["food"] = [...]   cache["directions"] = [...]
    ⚠️ COLLISION! Both modifying simultaneously

Result: Cache corruption, data loss, crashes

═══════════════════════════════════════════════════════════════
WITH THREAD SAFETY: Lock Mechanism
═══════════════════════════════════════════════════════════════

Thread A (User 1):        Thread B (User 2):
topic = "food"            topic = "directions"
    ↓                         ↓
Request lock...         Request lock...
LOCK ACQUIRED ✅         WAIT... (locked)
    ↓                         │ (waiting)
Read cache...                │
    ↓                         │
Write cache...               │
    ↓                         │
Release lock ✅           WAIT... (released)
                            ↓
                        LOCK ACQUIRED ✅
                            ↓
                        Read cache...
                            ↓
                        Write cache...
                            ↓
                        Release lock ✅

Result: Sequential access, no corruption, data integrity
```

## Key Insight: Why LRU Matters for Grammar Cache

```
═══════════════════════════════════════════════════════════════
LEARNER BEHAVIOR: Temporal Locality
═══════════════════════════════════════════════════════════════

Session 1 (Morning):     Session 2 (Evening):     Session 3 (Tomorrow):
- food                   - food                   - work
- family                 - food (repeated!)       - food (repeated!)
- food                   - hobbies                - food (repeated!)
- directions             - food (repeated!)       - daily routine
- food                   - travel                 - food (repeated!)

Pattern: Learner talks about food A LOT!
LRU Benefit: "food" stays in cache, never evicted
Performance: Instant lookups, no LLM calls for "food"

═══════════════════════════════════════════════════════════════
CONCURRENT USERS: Shared Cache Efficiency
═══════════════════════════════════════════════════════════════

User A (Berlin):         User B (Munich):         User C (Hamburg):
- food                   - food                   - family
- work                   - food                   - food
- food                   - directions             - food
- hobbies                - food                   - work

Shared Cache Topics:
1. food (accessed 7 times!) ← NEVER EVICTED
2. family (accessed 2 times)
3. work (accessed 2 times)
4. hobbies (accessed 1 time)
5. directions (accessed 1 time)

✓ Topic→grammar mapping is UNIVERSAL (same for all learners)
✓ All users benefit from each other's cache entries
✓ Massive performance gains for common topics
```

## Summary: LRU in 3 Points

1. **What**: Cache that evicts least recently used items when full
2. **Why**: Improves performance by caching frequently accessed data
3. **How**: `@lru_cache` decorator in Python + locks for thread safety

In GrammarCurriculumAgent:
- ✅ Speeds up topic→grammar lookups
- ✅ Reduces LLM API costs
- ✅ Enables safe concurrent access
- ✅ Automatically manages cache size
- ✅ Perfect fit for learner behavior (topic repetition)
