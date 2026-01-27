# /debt-audit

Complete 27-category tech debt scan with parallel analyzers.

## Usage

```
/debt-audit [path] [options]
```

### Options

- `--category <name>` - Analyze specific category only (can repeat)
- `--severity <level>` - Minimum severity to report (critical, high, medium, low)
- `--json` - Output as JSON for tooling integration
- `--fail-on <level>` - Exit with error if findings at this severity or above

### Examples

```bash
# Full audit of current directory
/debt-audit

# Audit specific path
/debt-audit ./src

# Security-focused audit
/debt-audit --category injection --category secrets --category auth

# CI/CD integration (fail on critical)
/debt-audit --fail-on critical --json

# Just operational debt
/debt-audit --category resilience --category observability --category slo
```

## Instructions

When the user runs `/debt-audit`:

1. **Run the audit orchestrator** to scan the codebase:

```bash
python ~/.claude/skills/tech-debt-zero/scripts/core/audit_orchestrator.py [path] [options]
```

2. **Present the findings** organized by severity:
   - CRITICAL findings first (security vulnerabilities, data exposure)
   - HIGH findings second (significant risk)
   - MEDIUM and LOW for completeness

3. **Provide a summary**:
   - Total findings count
   - Breakdown by category (Security, Operational, Architecture)
   - Top 5 most impacted files

4. **Suggest next steps**:
   - If CRITICAL findings: "Run `/fix-injection-debt` or `/fix-secrets-debt` immediately"
   - If many findings: "Run `/debt-prioritize` to get ROI-based ranking"
   - If tracking needed: "Run `/debt-track record` to track progress over time"

## Categories Analyzed

### Security (9)
1. Injection (SQL, XSS, command, SSRF, path traversal)
2. Cryptographic weaknesses
3. Session management
4. Authentication/Authorization
5. Security headers
6. Supply chain
7. Secrets management
8. Data privacy
9. Infrastructure security

### Operational (9)
10. Observability (logging, metrics, tracing)
11. Resilience (timeouts, circuit breakers)
12. Deployment (rollback, feature flags)
13. Configuration
14. SLO/Reliability
15. Alerting
16. Runbooks
17. Build/CI
18. Rate limiting

### Architecture (9)
19. SOLID violations
20. Coupling/Cohesion
21. Design anti-patterns
22. Domain model
23. API contracts
24. Schema evolution
25. Distributed systems
26. Event/Async
27. Legacy integration

## Output Format

### Text Output (default)

```
============================================================
TECH DEBT AUDIT REPORT
============================================================
Project: /path/to/project
Timestamp: 2024-01-15T10:30:45Z
Total Findings: 42

SUMMARY BY SEVERITY
----------------------------------------
  CRITICAL: 3
  HIGH: 12
  MEDIUM: 20
  LOW: 7

SUMMARY BY CATEGORY
----------------------------------------
  injection: 2
  secrets: 1
  resilience: 8
  ...

FINDINGS
============================================================

--- CRITICAL (3) ---

[injection-0001] SQL injection via template literal
  Category: injection
  Location: src/api/users.js:45
  Use parameterized queries instead of template literals.
  Fix: Use parameterized queries or prepared statements.

[secrets-0001] Hardcoded API key
  Category: secrets
  Location: src/config.js:12
  API key found in source code.
  Fix: Use environment variables or secrets manager.

...
```

### JSON Output (--json)

```json
{
  "timestamp": "2024-01-15T10:30:45Z",
  "project_path": "/path/to/project",
  "summary": {
    "total_findings": 42,
    "by_severity": {"critical": 3, "high": 12, "medium": 20, "low": 7},
    "by_category": {"injection": 2, "secrets": 1, ...}
  },
  "findings": [
    {
      "id": "injection-0001",
      "category": "injection",
      "severity": "critical",
      "title": "SQL injection via template literal",
      "file_path": "src/api/users.js",
      "line_number": 45,
      "remediation": "Use parameterized queries"
    }
  ]
}
```

## Safe Remediation Sequence

After audit, address findings in this order:

1. **CRITICAL security** - Immediate
2. **Add tests** to affected code before fixing
3. **Resilience** - Timeouts, circuit breakers
4. **Observability** - Logging, metrics
5. **Dependencies** - Security patches
6. **Auth/AuthZ** - Access control
7. **Architecture** - Refactoring (with tests)

## Integration

### Pre-commit Hook

```bash
#!/bin/bash
python ~/.claude/skills/tech-debt-zero/scripts/core/audit_orchestrator.py \
  --category injection --category secrets \
  --fail-on critical
```

### CI Pipeline

```yaml
- name: Tech Debt Audit
  run: |
    python ~/.claude/skills/tech-debt-zero/scripts/core/audit_orchestrator.py \
      --category security \
      --fail-on high \
      --json > debt-report.json
```
