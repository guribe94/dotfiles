---
description: Order lifecycle and state machine verification - ensure no invalid transitions or lost orders
argument-hint: [optional: order-manager-file]
---

# Order State Machine Audit

You are a Senior Trading Systems Engineer verifying order management logic.

**A bug in order handling = uncontrolled position = unlimited loss.**

$ARGUMENTS

## Constraints
- NO structural changes
- NO mutexes unless proven necessary
- Every fix needs a failing-then-passing test

## Phase 1: Map All Order States

Find and document every possible order state:

```
PENDING_NEW      → Order created, not yet sent
SENT             → Sent to exchange, awaiting ack
OPEN/ACTIVE      → Acknowledged, resting on book
PARTIALLY_FILLED → Some quantity executed
FILLED           → Fully executed
PENDING_CANCEL   → Cancel request sent
CANCELED         → Successfully canceled
REJECTED         → Exchange rejected order
EXPIRED          → Time-in-force expired
ERROR            → Internal error state
```

For each state, identify:
- Where it's set in code
- What triggers transition TO this state
- What triggers transition FROM this state

## Phase 2: Validate State Transitions

Create the state transition matrix:

```
From\To    | SENT | OPEN | PARTIAL | FILLED | P_CANCEL | CANCELED | REJECTED |
-----------|------|------|---------|--------|----------|----------|----------|
PENDING    |  ✓   |      |         |        |          |          |    ✓     |
SENT       |      |  ✓   |    ✓    |   ✓    |    ✓     |          |    ✓     |
OPEN       |      |      |    ✓    |   ✓    |    ✓     |    ✓     |          |
PARTIAL    |      |      |    ✓    |   ✓    |    ✓     |    ✓     |          |
P_CANCEL   |      |      |    ✓    |   ✓    |          |    ✓     |    ✓     |
```

Verify in code:
- [ ] Invalid transitions are impossible (not just logged)
- [ ] Terminal states (FILLED, CANCELED, REJECTED) cannot transition
- [ ] PENDING_CANCEL + FILL race handled correctly

## Phase 3: Quantity Tracking

For partial fills:
- [ ] Remaining quantity = original - sum(fill quantities)
- [ ] Remaining quantity never goes negative
- [ ] Duplicate fill messages are idempotent
- [ ] Fill quantity updates position atomically

Test scenarios:
```
Order: BUY 100 @ 50000
Fill 1: 30 → remaining = 70, position = +30
Fill 2: 30 → remaining = 40, position = +60  
Fill 2 (dup): → remaining = 40, position = +60 (no change!)
Fill 3: 40 → remaining = 0, state = FILLED, position = +100
```

## Phase 4: Order ID Management

Verify:
- [ ] Client order ID generation is unique
- [ ] No collisions possible (UUID or monotonic counter)
- [ ] Exchange order ID mapped correctly after ack
- [ ] Lookup by either ID works correctly
- [ ] Old orders cleaned up (no memory leak)

## Phase 5: Race Conditions

Check these scenarios:
```
1. Cancel request crosses with fill
   - Sent: CANCEL
   - Received: FILL (before cancel ack)
   - Result: Position updated? Cancel fails gracefully?

2. Amend request crosses with fill  
   - Sent: AMEND quantity 100→50
   - Received: FILL 70
   - Result: Amend rejected? Position correct?

3. Duplicate execution reports
   - Received: FILL 30
   - Received: FILL 30 (same exec ID)
   - Result: Position = 30, not 60

4. Out-of-order messages
   - Received: FILL (before OPEN ack)
   - Result: Order state and position correct?
```

## Phase 6: Orphan Order Detection

Verify:
- [ ] Orders without response after timeout are handled
- [ ] Reconnection reconciles order state with exchange
- [ ] Stale orders are detected and cleaned up
- [ ] Position matches sum of open orders + fills

## Output Format

```markdown
# Order State Machine Audit

## State Transition Diagram
[Mermaid or ASCII diagram of actual states found]

## Issues Found

### [CRITICAL] Invalid Transition Possible
Location: file:line
From: STATE_A → To: STATE_B
Why invalid: [explanation]
Fix: [code change]

### [HIGH] Race Condition
Scenario: [description]
Current behavior: [what happens]
Correct behavior: [what should happen]
Fix: [code change]

## Verified Correct
- [ ] All state transitions validated
- [ ] Quantity tracking verified
- [ ] Idempotent fill handling confirmed
- [ ] Race conditions handled
```

**Start by finding the Order class/struct and mapping all possible states.**
