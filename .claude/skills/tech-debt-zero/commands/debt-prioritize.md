# /debt-prioritize

ROI-based ranking of tech debt findings with exploitability/exposure factors.

## Usage

```
/debt-prioritize [input-file] [options]
```

### Options

- `--top <N>` - Show only top N findings
- `--category <name>` - Filter by priority category (critical, quick_win, high_value, standard, defer)
- `--json` - Output as JSON

### Examples

```bash
# Prioritize findings from audit
/debt-audit --json | /debt-prioritize

# Show top 10 quick wins
/debt-prioritize --category quick_win --top 10

# Prioritize from saved audit file
/debt-prioritize audit-results.json
```

## Instructions

When the user runs `/debt-prioritize`:

1. **Read audit findings** from input (file or previous audit)

2. **Calculate ROI** for each finding:
   ```
   ROI = (Impact × Urgency) / Effort
   ```

3. **Categorize findings**:
   - **Critical** - All CRITICAL severity (regardless of ROI)
   - **Quick Wins** - ROI > 5.0 (high value, low effort)
   - **High Value** - ROI 2.0-5.0
   - **Standard** - ROI 1.0-2.0
   - **Defer** - ROI < 1.0 (track but deprioritize)

4. **Present prioritized list** with ROI scores and recommendations

5. **Suggest action plan** based on results

## ROI Calculation

### Impact Score (1-10)

Weighted average of:

| Factor | Weight | Description |
|--------|--------|-------------|
| Exploitability | 25% | How easily can this be exploited? |
| Data Sensitivity | 25% | What data is at risk? |
| Blast Radius | 20% | How many users/systems affected? |
| Compliance | 15% | Regulatory/audit implications? |
| Availability | 10% | Service reliability impact? |
| Velocity | 5% | Impact on dev productivity? |

### Urgency Multiplier (1.0-2.0)

Based on severity and time-sensitive factors:

| Severity | Multiplier |
|----------|------------|
| CRITICAL | 2.0 |
| HIGH | 1.5 |
| MEDIUM | 1.2 |
| LOW | 1.0 |

Additional modifiers:
- Active exploitation: 2.0
- Compliance deadline: 1.8
- Audit finding: 1.5

### Effort Score (1-10)

Based on estimated hours:

| Size | Hours | Score |
|------|-------|-------|
| XS | 0-2 | 1 |
| S | 2-4 | 2 |
| M | 4-16 | 4 |
| L | 16-40 | 7 |
| XL | 40-80 | 9 |
| XXL | 80+ | 10 |

## Output Format

```
======================================================================
TECH DEBT PRIORITIZATION REPORT
======================================================================

### CRITICAL (Address Immediately)

#    ID                   Category        ROI   Effort Title
----------------------------------------------------------------------
1    injection-0001       injection       5.5   S      SQL injection in /api/search

### QUICK WINS (ROI > 5.0)

#    ID                   Category        ROI   Effort Title
----------------------------------------------------------------------
2    secrets-0001         secrets        15.0   XS     Hardcoded API key in config
3    rate_limits-0001     rate_limits     6.0   S      Missing rate limit on /login

### HIGH VALUE (ROI 2.0-5.0)

#    ID                   Category        ROI   Effort Title
----------------------------------------------------------------------
4    resilience-0001      resilience      3.5   M      Missing timeout on payment service
5    auth-0001            auth            2.8   M      Missing auth on admin endpoint

### STANDARD (ROI 1.0-2.0)
...

### DEFER (ROI < 1.0)
...

======================================================================
ROI = (Impact × Urgency) / Effort
Higher ROI = Higher priority for remediation
```

## Implementation

Run the ROI calculator:

```bash
python ~/.claude/skills/tech-debt-zero/scripts/core/calculate_roi.py [input] [options]
```

## Suggested Workflows

### Quick Win Sprint

Focus on ROI > 5.0 findings:
1. Run `/debt-prioritize --category quick_win`
2. Address top 5-10 quick wins
3. Re-run audit to verify fixes
4. Track progress with `/debt-track record`

### Security Sprint

Focus on security findings by ROI:
1. Run `/debt-audit --category injection --category secrets --category auth --json`
2. Pipe to `/debt-prioritize`
3. Address CRITICAL first, then quick wins
4. Verify with security scan

### Technical Debt Reduction

Systematic debt reduction:
1. Run full audit
2. Prioritize all findings
3. Create tickets for top 20 by ROI
4. Track progress weekly
