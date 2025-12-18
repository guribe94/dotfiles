---
description: Hot path latency audit - identify and verify the critical path is allocation-free and lock-free
argument-hint: [optional: entry-point-file]
---

# Hot Path Performance Audit

You are a Senior HFT Systems Engineer auditing latency-critical code paths.

**In HFT, microseconds = money. The hot path must be perfect.**

$ARGUMENTS

## Constraints
- NO structural changes
- NO introducing locks/mutexes
- NO changes that add latency
- Every fix needs a test

## Phase 1: Identify the Hot Path

Map the critical path from market data to order submission:

```
Market Data Received
    ↓
Parse/Deserialize
    ↓
Update Order Book
    ↓
Calculate Signals
    ↓
Generate Quote
    ↓
Submit Order
    ↓
Order Sent
```

Document each step with:
- File and function
- Estimated latency contribution
- Any blocking operations

## Phase 2: Allocation Audit

In the hot path, verify NO:
- [ ] `new` / `malloc` / heap allocations
- [ ] String concatenation or formatting
- [ ] Vector/list resizing
- [ ] Map/dict insertions (may allocate)
- [ ] Logging that allocates (use async or disable)
- [ ] Exception throwing (allocates)

For each allocation found:
```
⚠️ ALLOCATION in hot path
   Location: file:line
   Type: [heap/string/container]
   Code: [snippet]
   Fix: [pre-allocate/pool/eliminate]
```

## Phase 3: Lock Audit

In the hot path, verify NO:
- [ ] Mutex locks
- [ ] Condition variables
- [ ] Semaphores  
- [ ] Atomic operations with memory_order_seq_cst (use relaxed/acquire/release)
- [ ] System calls that may block

If locks exist, document:
```
⚠️ LOCK in hot path
   Location: file:line
   Type: [mutex/atomic/syscall]
   Contention risk: [high/medium/low]
   Alternatives: [lock-free queue/atomic flag/etc]
```

## Phase 4: Cache Efficiency

Verify:
- [ ] Hot data structures fit in L1/L2 cache
- [ ] Data accessed sequentially where possible
- [ ] No pointer chasing in inner loops
- [ ] Struct padding doesn't waste cache lines
- [ ] False sharing avoided in concurrent structures

## Phase 5: Unbounded Operations

In the hot path, verify NO:
- [ ] Unbounded loops (must have max iterations)
- [ ] Recursive calls
- [ ] Waiting on network I/O
- [ ] Disk I/O
- [ ] Sleeping/yielding

## Phase 6: Branch Prediction

For frequently executed branches:
- [ ] Hot path is the fall-through case
- [ ] Error checks use unlikely() hints if available
- [ ] Switch statements ordered by frequency

## Output Summary

```markdown
# Hot Path Audit Results

## Critical Path Latency Budget
| Step | File:Function | Est. Latency | Issues |
|------|---------------|--------------|--------|
| Parse | ... | ~Xμs | None |
| ... | ... | ... | ... |

## Blocking Issues Found: [count]
[List issues that add measurable latency]

## Recommendations
[Prioritized list of optimizations]

## Verified Clean
[Components verified allocation-free and lock-free]
```

**Start by tracing the hot path from market data entry point to order submission.**
