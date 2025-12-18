---
description: Edge case and failure mode audit - ensure system fails safely without losing money
argument-hint: [optional: module-to-focus-on]
---

# Edge Cases & Failure Modes Audit

You are a Chaos Engineer for trading systems. Your job: find ways the system loses money.

**Murphy's Law applies double in production trading. Everything that can go wrong, will.**

$ARGUMENTS

## Constraints
- NO structural changes
- NO adding latency to hot path
- Every fix needs a test

## Phase 1: Numeric Edge Cases

Test these scenarios:

### Division Operations
Find ALL division operations and verify:
- [ ] Divisor can never be zero
- [ ] If it can be zero, what happens?

```python
# Find patterns like:
spread = (ask - bid) / mid  # What if mid = 0?
pct_change = (new - old) / old  # What if old = 0?
vwap = total_value / total_volume  # What if volume = 0?
```

### Overflow/Underflow
- [ ] quantity × price doesn't overflow
- [ ] position + fill doesn't overflow
- [ ] timestamp arithmetic handles wrap-around
- [ ] Fee calculations don't underflow to negative

### Boundary Values
Test with:
```
price = 0
price = MAX_INT
quantity = 0
quantity = 1 (minimum lot)
quantity = MAX_POSITION
spread = 0
spread = negative (crossed book)
```

### Floating Point
- [ ] Money calculations use Decimal, not float
- [ ] Comparisons use epsilon, not ==
- [ ] No precision loss in aggregations

## Phase 2: Network Failure Modes

### WebSocket Disconnect
- [ ] Automatic reconnection works
- [ ] Order state reconciled after reconnect
- [ ] Position reconciled after reconnect
- [ ] No duplicate orders sent on reconnect
- [ ] Trading paused until reconciliation complete

### Partial Messages
- [ ] Incomplete JSON handled gracefully
- [ ] Buffer overflow impossible
- [ ] Message framing errors detected

### Duplicate Messages
- [ ] Duplicate order acks are idempotent
- [ ] Duplicate fills don't double-count
- [ ] Duplicate cancels don't error

### Out-of-Order Messages
- [ ] Fill before ack handled
- [ ] Cancel ack before order ack handled
- [ ] Sequence gaps detected and recovered

### Timeout Handling
- [ ] Order timeout cancels order OR marks uncertain
- [ ] No orphan orders left on exchange
- [ ] Timeout doesn't cause position mismatch

## Phase 3: Exchange Edge Cases

### Rate Limiting
- [ ] Rate limit errors handled (not crashed)
- [ ] Back-off implemented
- [ ] Orders queued or dropped gracefully
- [ ] No position exposure during rate limit

### Exchange Errors
Map all exchange error codes and verify handling:
```
INSUFFICIENT_BALANCE → ?
INVALID_PRICE → ?
INVALID_QUANTITY → ?
MARKET_CLOSED → ?
ORDER_NOT_FOUND → ?
POSITION_LIMIT → ?
```

### Exchange-Initiated Events
- [ ] Exchange cancels our order → position correct?
- [ ] Exchange liquidates position → handled?
- [ ] Exchange maintenance → trading stops?
- [ ] Price band rejection → retry logic?

### Market Conditions
- [ ] Flash crash (price drops 50% in seconds)
- [ ] No liquidity (empty book)
- [ ] Crossed book (bid > ask)
- [ ] Stale quotes (no updates for N seconds)

## Phase 4: Internal Failure Modes

### Memory
- [ ] Order book doesn't grow unbounded
- [ ] Old orders cleaned up
- [ ] No memory leaks in long-running process

### State Corruption
- [ ] Position can't become inconsistent with fills
- [ ] Order state can't become inconsistent with exchange
- [ ] Config changes don't corrupt running state

### Startup/Shutdown
- [ ] Clean shutdown cancels all open orders
- [ ] Restart reconciles with exchange state
- [ ] Partial startup (some connections fail) handled

## Phase 5: Configuration Edge Cases

### Invalid Config
- [ ] Negative spread → rejected or clamped
- [ ] Position limit = 0 → no trading
- [ ] Invalid API key → clear error message
- [ ] Missing required field → startup fails safely

### Hot Reload
- [ ] Config change during open positions → safe?
- [ ] Invalid config rejected without affecting running config

## Output Format

```markdown
# Edge Case Audit Results

## Critical Failures Found
[Issues that WILL cause loss]

### [CRITICAL] Division by Zero
Location: file:line
Trigger: When volume = 0
Impact: Crash or undefined behavior
Fix: Add guard condition

## High Risk Scenarios
[Issues that could cause loss under specific conditions]

## Verified Safe
- [ ] All division operations guarded
- [ ] Overflow impossible in critical calculations
- [ ] Network failures trigger safe shutdown
- [ ] Exchange errors handled gracefully

## Recommended Tests
[List of edge case tests that should be added]
```

**Start by grep-ing for division operations, then work through each phase systematically.**
