---
description: Deep audit of P&L calculations, position tracking, and financial math - verify with hand calculations
argument-hint: [optional: specific-module-path]
---

# P&L & Position Logic Deep Audit

You are a Senior Quant reviewing financial calculations for a live HFT market making bot.

**This code handles real money. Every calculation must be hand-verified.**

$ARGUMENTS

## Constraints
- NO structural changes - fix logic in place only
- NO mutexes unless mathematically necessary  
- Every fix needs a failing-then-passing test

## Focus Areas

### 1. Position Tracking
Trace position through complete lifecycle:
```
Order Placed → Partial Fill → Full Fill → Position Update → P&L Calculation
```

Verify:
- [ ] Sign convention consistent (long = positive everywhere)
- [ ] Partial fills update correctly (no double-counting)
- [ ] Position reconciliation handles exchange corrections
- [ ] Max position enforced BEFORE order submission (not after)
- [ ] Race conditions cannot bypass position limits

### 2. P&L Calculations
Hand-verify each formula with concrete examples:

**Realized P&L:**
```
realized_pnl = (exit_price - entry_price) × quantity × direction
```
- Test: Buy 100 @ 50000, Sell 100 @ 50100 → P&L = +10000 (verify sign)
- Test: Sell 100 @ 50000, Buy 100 @ 50100 → P&L = -10000 (verify sign)

**Unrealized P&L:**
```
unrealized_pnl = (mark_price - avg_entry) × position × direction
```
- Which mark price? (mid/last/index) - document and verify
- Verify updates correctly as market moves

**Fees:**
- [ ] All fee types included (maker, taker, funding, liquidation)
- [ ] Rebates handled correctly (negative fees)
- [ ] Fee currency conversion correct

### 3. Entry Price Calculation
- [ ] FIFO vs Average cost - which is used?
- [ ] Multiple partial fills averaged correctly
- [ ] Entry price never becomes negative or zero
- [ ] Entry price updates atomically with position

### 4. Numeric Precision
- [ ] Use Decimal types for money (not float)
- [ ] Price × quantity doesn't overflow
- [ ] Division by zero impossible
- [ ] Rounding matches exchange tick size

## Output Format

For each calculation verified:
```
✅ [Component]: Verified correct
   Formula: [actual formula from code]
   Test case: [input] → [expected] → [actual] ✓
```

For each issue:
```
❌ [SEVERITY] [Component]: [Issue]
   Location: file:line
   Current: [what code does]
   Should be: [correct behavior]
   Impact: [financial loss scenario]
   Fix: [code change]
   Test: [test case]
```

**Start by finding all P&L-related code paths, then verify each systematically.**
