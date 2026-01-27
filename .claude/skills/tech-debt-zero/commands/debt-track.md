# /debt-track

Progress tracking with trend analysis for tech debt reduction.

## Usage

```
/debt-track <command> [options]
```

### Commands

- `record` - Record a new snapshot from audit results
- `trend` - Show trend analysis over time
- `history` - Show snapshot history

### Options

- `--project <name>` - Project identifier (required)
- `--days <N>` - Time range for analysis (default: 30)
- `--json` - Output as JSON

### Examples

```bash
# Record snapshot after audit
/debt-audit --json | /debt-track record --project my-app

# View 30-day trend
/debt-track trend --project my-app

# View 90-day history
/debt-track history --project my-app --days 90

# Export trend as JSON for dashboard
/debt-track trend --project my-app --json
```

## Instructions

When the user runs `/debt-track`:

### For `record`:

1. **Read audit results** from input
2. **Store snapshot** with timestamp and project identifier
3. **Confirm recording** with finding counts

### For `trend`:

1. **Load historical snapshots** for the project
2. **Calculate trends**:
   - Total change (debt increased/decreased)
   - Velocity (findings per day)
   - Burn-down estimate
3. **Identify patterns**:
   - Which categories are improving?
   - Which are getting worse?
   - What got resolved?
   - What's new?

### For `history`:

1. **Display snapshot timeline**
2. **Show totals and severity breakdown** per snapshot

## Output Format

### Trend Report

```
============================================================
TECH DEBT TREND REPORT
============================================================
Project: my-app
Period: 2024-01-01 to 2024-01-30

OVERALL TREND
----------------------------------------
  Debt DECREASED by 15 findings
  Velocity: -0.5 findings/day
  Estimated time to zero debt: 84 days

BY SEVERITY
----------------------------------------
  CRITICAL: -3
  HIGH: -8
  MEDIUM: -4
  LOW: 0

TOP CATEGORY CHANGES
----------------------------------------
  secrets: -5
  injection: -3
  resilience: -2
  coupling: +2
  observability: -1

RESOLVED (8)
----------------------------------------
  [critical] SQL injection in user search
  [critical] Hardcoded AWS keys
  [high] Missing timeout on payment API
  [high] Rate limit bypass on login
  ... and 4 more

NEW (3)
----------------------------------------
  [medium] New god object in OrderService
  [medium] Missing circuit breaker on inventory
  [low] Unused dependency
```

### History

```
Snapshot history for my-app
------------------------------------------------------------
2024-01-30T10:00:00  Total: 42  Critical: 0  High: 8
2024-01-23T10:00:00  Total: 48  Critical: 1  High: 12
2024-01-16T10:00:00  Total: 52  Critical: 2  High: 14
2024-01-09T10:00:00  Total: 55  Critical: 3  High: 15
2024-01-02T10:00:00  Total: 57  Critical: 3  High: 16
```

## Implementation

Run the metrics tracker:

```bash
python ~/.claude/skills/tech-debt-zero/scripts/core/track_metrics.py <command> [options]
```

## Storage

Snapshots are stored in SQLite at:
```
~/.tech-debt-metrics.db
```

## Metrics Tracked

- **Total findings** per snapshot
- **By severity** (critical, high, medium, low)
- **By category** (27 categories)
- **Individual findings** (for resolved/new detection)
- **Average ROI score** (if prioritization data included)

## Workflow Integration

### Weekly Debt Review

```bash
# Run audit
/debt-audit --json > audit.json

# Record snapshot
/debt-track record --project my-app < audit.json

# View trend
/debt-track trend --project my-app --days 7
```

### Sprint Planning

```bash
# View what got resolved and what's new
/debt-track trend --project my-app --days 14

# Prioritize remaining debt
/debt-prioritize audit.json --top 10
```

### Monthly Report

```bash
# Generate trend report for stakeholders
/debt-track trend --project my-app --days 30 --json > monthly-report.json

# View full history
/debt-track history --project my-app --days 90
```

## Dashboard Integration

Export JSON for visualization:

```bash
/debt-track trend --project my-app --json | jq '{
  velocity: .trend.velocity,
  total_change: .trend.total_change,
  resolved_count: (.resolved | length),
  new_count: (.new | length),
  burn_down: .trend.burn_down_estimate
}'
```
