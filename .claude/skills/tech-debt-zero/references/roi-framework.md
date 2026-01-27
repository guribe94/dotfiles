# ROI Framework for Tech Debt Prioritization

## Overview

This framework calculates Return on Investment (ROI) for tech debt remediation, enabling data-driven prioritization. The formula balances impact against effort to identify the highest-value work.

## Formula

```
ROI = (Impact Score × Urgency Multiplier) / Effort Score
```

Where:
- **Impact Score**: 1-10 based on multiple factors
- **Urgency Multiplier**: 1.0-2.0 based on time sensitivity
- **Effort Score**: 1-10 based on implementation complexity

---

## Impact Scoring (1-10)

### Factor 1: Exploitability (Weight: 25%)

How easily can this be exploited?

| Score | Criteria |
|-------|----------|
| 10 | Public endpoint, no authentication required, known exploit exists |
| 8 | Authenticated endpoint, but low-privilege user can exploit |
| 6 | Requires specific conditions or internal access |
| 4 | Requires privileged access or chained vulnerabilities |
| 2 | Theoretical only, no practical exploit path |

### Factor 2: Data Sensitivity (Weight: 25%)

What data is at risk?

| Score | Criteria |
|-------|----------|
| 10 | Credentials, encryption keys, payment data |
| 8 | PII (SSN, medical, financial records) |
| 6 | Personal data (email, name, address) |
| 4 | Business data (non-sensitive) |
| 2 | Public or non-sensitive data |

### Factor 3: Blast Radius (Weight: 20%)

How many users/systems affected?

| Score | Criteria |
|-------|----------|
| 10 | All users, all environments |
| 8 | All users in production |
| 6 | Subset of users (one tenant, one region) |
| 4 | Single user or isolated system |
| 2 | Development/test only |

### Factor 4: Compliance Impact (Weight: 15%)

Regulatory and audit implications?

| Score | Criteria |
|-------|----------|
| 10 | Active violation, audit finding, legal exposure |
| 8 | Clear compliance gap (GDPR, SOC2, PCI-DSS, HIPAA) |
| 6 | Best practice violation, potential future issue |
| 4 | Internal policy violation |
| 2 | No compliance impact |

### Factor 5: Availability Impact (Weight: 10%)

Service reliability implications?

| Score | Criteria |
|-------|----------|
| 10 | Complete service outage |
| 8 | Major feature unavailable |
| 6 | Degraded performance, partial outage |
| 4 | Minor impact, workaround available |
| 2 | No availability impact |

### Factor 6: Developer Velocity (Weight: 5%)

Impact on team productivity?

| Score | Criteria |
|-------|----------|
| 10 | Blocks all development |
| 8 | Significantly slows feature work |
| 6 | Causes regular friction/workarounds |
| 4 | Minor inconvenience |
| 2 | No impact on velocity |

### Calculating Total Impact

```python
def calculate_impact(factors):
    weights = {
        'exploitability': 0.25,
        'data_sensitivity': 0.25,
        'blast_radius': 0.20,
        'compliance': 0.15,
        'availability': 0.10,
        'velocity': 0.05
    }

    total = sum(factors[k] * weights[k] for k in weights)
    return round(total, 1)
```

---

## Urgency Multiplier (1.0-2.0)

Time-sensitive factors that increase priority:

| Multiplier | Criteria |
|------------|----------|
| 2.0 | Active exploitation, imminent audit, regulatory deadline |
| 1.5 | Known vulnerability with public exploit, compliance deadline approaching |
| 1.2 | Recent security advisory, upcoming audit |
| 1.0 | No time pressure |

---

## Effort Scoring (1-10)

### Size-Based Estimation

| Score | Size | Hours | Description |
|-------|------|-------|-------------|
| 1-2 | XS | 0-2 | One-line fix, config change |
| 2-3 | S | 2-4 | Single function/file change |
| 4-5 | M | 4-16 | Multiple files, limited scope |
| 6-7 | L | 16-40 | Significant refactoring, new components |
| 8-9 | XL | 40-80 | Major rewrite, architectural change |
| 10 | XXL | 80+ | Multi-sprint initiative |

### Effort Factors

Consider these when scoring:

1. **Testing Requirements**
   - Existing test coverage?
   - New tests needed?
   - Integration/E2E tests required?

2. **Risk of Regression**
   - How critical is the affected code?
   - How well is it tested?
   - Rollback complexity?

3. **Dependencies**
   - Other teams involved?
   - External service changes?
   - Database migrations?

4. **Knowledge Requirements**
   - Domain expertise needed?
   - Security expertise needed?
   - Learning curve?

---

## ROI Categories

Based on calculated ROI, debt falls into categories:

| Category | ROI Range | Action |
|----------|-----------|--------|
| **Critical** | Any CRITICAL severity | Immediate, regardless of ROI |
| **Quick Wins** | > 5.0 | Do now, high value, low effort |
| **High Value** | 2.0 - 5.0 | Prioritize in current sprint |
| **Standard** | 1.0 - 2.0 | Schedule in backlog |
| **Low Priority** | 0.5 - 1.0 | Consider when convenient |
| **Defer** | < 0.5 | Document and revisit quarterly |

---

## Example Calculations

### Example 1: SQL Injection in Public API

```
Factors:
- Exploitability: 10 (public, no auth)
- Data Sensitivity: 8 (user PII)
- Blast Radius: 10 (all users)
- Compliance: 8 (GDPR violation)
- Availability: 4 (could cause issues)
- Velocity: 2 (no dev impact)

Impact = (10×0.25) + (8×0.25) + (10×0.20) + (8×0.15) + (4×0.10) + (2×0.05)
       = 2.5 + 2.0 + 2.0 + 1.2 + 0.4 + 0.1
       = 8.2

Urgency: 2.0 (known vulnerability class)
Effort: 3 (parameterized queries, 4-8 hours)

ROI = (8.2 × 2.0) / 3 = 5.5 → Quick Win (but also CRITICAL severity)
```

### Example 2: Missing Timeout on Internal API

```
Factors:
- Exploitability: 2 (internal only)
- Data Sensitivity: 2 (no data at risk)
- Blast Radius: 6 (affects service)
- Compliance: 2 (none)
- Availability: 8 (causes cascading failures)
- Velocity: 4 (debugging time)

Impact = (2×0.25) + (2×0.25) + (6×0.20) + (2×0.15) + (8×0.10) + (4×0.05)
       = 0.5 + 0.5 + 1.2 + 0.3 + 0.8 + 0.2
       = 3.5

Urgency: 1.0 (no time pressure)
Effort: 2 (add timeout config)

ROI = (3.5 × 1.0) / 2 = 1.75 → Standard priority
```

### Example 3: God Object Refactoring

```
Factors:
- Exploitability: 2 (no security impact)
- Data Sensitivity: 2 (no data at risk)
- Blast Radius: 4 (one module)
- Compliance: 2 (none)
- Availability: 2 (no impact)
- Velocity: 8 (major friction)

Impact = (2×0.25) + (2×0.25) + (4×0.20) + (2×0.15) + (2×0.10) + (8×0.05)
       = 0.5 + 0.5 + 0.8 + 0.3 + 0.2 + 0.4
       = 2.7

Urgency: 1.0 (no time pressure)
Effort: 7 (significant refactoring, tests)

ROI = (2.7 × 1.0) / 7 = 0.39 → Defer (but track)
```

---

## Prioritization Output

The `/debt-prioritize` command produces:

```
## Tech Debt Prioritization Report

### Critical (Address Immediately)
| # | Issue | Impact | Effort | ROI | Category |
|---|-------|--------|--------|-----|----------|
| 1 | SQL injection in /api/search | 8.2 | 3 | 5.5 | Security |

### Quick Wins (ROI > 5.0)
| # | Issue | Impact | Effort | ROI | Category |
|---|-------|--------|--------|-----|----------|
| 2 | Hardcoded API key in config | 7.5 | 1 | 15.0 | Security |
| 3 | Missing rate limit on /login | 6.0 | 2 | 6.0 | Operations |

### High Value (ROI 2.0-5.0)
...

### Backlog (ROI < 2.0)
...
```

---

## Automation

The ROI calculation is automated in `scripts/core/calculate_roi.py`:

```python
def prioritize_debt(findings):
    """
    Takes audit findings, calculates ROI, returns prioritized list.
    """
    prioritized = []

    for finding in findings:
        impact = calculate_impact(finding.factors)
        urgency = calculate_urgency(finding)
        effort = estimate_effort(finding)

        roi = (impact * urgency) / effort

        prioritized.append({
            'finding': finding,
            'impact': impact,
            'urgency': urgency,
            'effort': effort,
            'roi': roi,
            'category': categorize_roi(roi, finding.severity)
        })

    # Sort by: severity (CRITICAL first), then ROI descending
    return sorted(prioritized,
                  key=lambda x: (-severity_rank(x), -x['roi']))
```

---

## Recalibration

Review and adjust weights quarterly based on:
1. Incident post-mortems (what debt caused issues?)
2. Velocity metrics (what debt slowed the team?)
3. Audit findings (what was flagged?)
4. Customer impact (what affected users?)
