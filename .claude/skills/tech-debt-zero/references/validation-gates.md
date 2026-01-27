# Validation Gates

Production-ready checklists for verifying tech debt remediation.

---

## Pre-Merge Gates

### Security Gate

```yaml
gate: security
blocking: true
checks:
  - name: no-critical-vulnerabilities
    command: debt-audit --category security --severity critical
    fail_if: findings > 0

  - name: no-secrets
    command: detect-secrets scan --all-files
    fail_if: findings > 0

  - name: dependency-audit
    command: npm audit --audit-level high
    fail_if: exit_code != 0

  - name: sast-scan
    command: semgrep --config=auto --error
    fail_if: exit_code != 0
```

### Resilience Gate

```yaml
gate: resilience
blocking: true
checks:
  - name: timeouts-configured
    command: debt-audit --category resilience --check timeouts
    fail_if: missing_timeouts > 0

  - name: circuit-breakers
    command: debt-audit --category resilience --check circuit-breakers
    fail_if: unprotected_calls > 0
```

### Quality Gate

```yaml
gate: quality
blocking: true
checks:
  - name: test-coverage
    threshold: 80%
    exclude: generated/**

  - name: type-check
    command: tsc --noEmit --strict
    fail_if: exit_code != 0

  - name: lint
    command: eslint . --max-warnings 0
    fail_if: exit_code != 0
```

---

## Pre-Deployment Gates

### Staging Validation

```yaml
gate: staging-validation
blocking: true
checks:
  - name: integration-tests
    command: npm run test:integration
    timeout: 10m

  - name: health-check
    command: curl -f $STAGING_URL/health
    retries: 3

  - name: smoke-tests
    command: npm run test:smoke
    timeout: 5m
```

### Production Readiness

```yaml
gate: production-readiness
blocking: true
checks:
  - name: rollback-tested
    manual: true
    description: Verify rollback procedure works

  - name: monitoring-configured
    checks:
      - dashboards_exist
      - alerts_configured
      - runbook_linked

  - name: feature-flag-ready
    checks:
      - flag_exists
      - kill_switch_tested
```

---

## Category-Specific Validation

### Security Remediation

#### Injection Fix Validation

```markdown
## Before Marking Complete

- [ ] Vulnerable code pattern removed
- [ ] Parameterized queries/prepared statements used
- [ ] Input validation added
- [ ] Output encoding applied (for XSS)
- [ ] Unit test for malicious input
- [ ] Integration test for attack scenario
- [ ] Security scan passes
- [ ] Code review by security-aware developer
```

#### Secrets Fix Validation

```markdown
## Before Marking Complete

- [ ] Secret removed from codebase
- [ ] Git history cleaned (if necessary)
- [ ] Secret rotated
- [ ] New secret in secure storage (Vault, AWS Secrets Manager, etc.)
- [ ] Application reads from secure storage
- [ ] Audit logging for secret access
- [ ] Old secret invalidated
- [ ] No secrets in logs verified
```

#### Auth Fix Validation

```markdown
## Before Marking Complete

- [ ] Auth middleware added to route
- [ ] Authorization check implemented
- [ ] Test for unauthenticated access (should fail)
- [ ] Test for unauthorized access (should fail)
- [ ] Test for authorized access (should succeed)
- [ ] Session regeneration after privilege change
- [ ] Audit logging for auth events
```

### Operational Remediation

#### Timeout Fix Validation

```markdown
## Before Marking Complete

- [ ] Timeout configured on HTTP client
- [ ] Timeout configured on database connection
- [ ] Timeout value is reasonable (not too short/long)
- [ ] Timeout error handled gracefully
- [ ] Metric emitted on timeout
- [ ] Alert configured for timeout rate
- [ ] Test simulates timeout scenario
```

#### Circuit Breaker Validation

```markdown
## Before Marking Complete

- [ ] Circuit breaker wraps external call
- [ ] Open state threshold configured
- [ ] Half-open state tested
- [ ] Fallback behavior defined
- [ ] Fallback tested
- [ ] Metrics for circuit state
- [ ] Alert for circuit open events
- [ ] Dashboard shows circuit health
```

#### Observability Fix Validation

```markdown
## Before Marking Complete

- [ ] Structured logging format (JSON)
- [ ] Correlation ID propagated
- [ ] No sensitive data in logs
- [ ] Appropriate log levels
- [ ] Metrics emitted (RED: rate, errors, duration)
- [ ] Traces connected across services
- [ ] Dashboard updated
- [ ] Alerts configured
```

### Architecture Remediation

#### Coupling Fix Validation

```markdown
## Before Marking Complete

- [ ] Coupling metrics measured before
- [ ] Interface extracted
- [ ] Dependency injection used
- [ ] Coupling metrics improved
- [ ] No circular dependencies introduced
- [ ] Tests still pass
- [ ] No performance regression
```

#### SOLID Fix Validation

```markdown
## Before Marking Complete

- [ ] Violation identified and documented
- [ ] Tests added for existing behavior
- [ ] Refactoring applied
- [ ] Single responsibility achieved (SRP)
- [ ] Extension without modification possible (OCP)
- [ ] Substitutability maintained (LSP)
- [ ] No unused interface methods (ISP)
- [ ] Dependencies on abstractions (DIP)
- [ ] Tests still pass
- [ ] Code review approved
```

---

## Automated Validation Scripts

### Security Validation

```python
def validate_security_fix(finding_id: str) -> ValidationResult:
    """Validate a security fix is complete."""

    finding = get_finding(finding_id)

    checks = [
        check_vulnerability_removed(finding),
        check_test_exists(finding),
        check_scan_passes(finding),
        check_code_review_approved(finding),
    ]

    if finding.category == 'secrets':
        checks.extend([
            check_secret_rotated(finding),
            check_history_clean(finding),
        ])

    return ValidationResult(
        passed=all(c.passed for c in checks),
        checks=checks
    )
```

### Resilience Validation

```python
def validate_resilience_fix(finding_id: str) -> ValidationResult:
    """Validate a resilience fix is complete."""

    finding = get_finding(finding_id)

    checks = [
        check_timeout_configured(finding),
        check_error_handled(finding),
        check_metric_emitted(finding),
        check_test_exists(finding),
    ]

    if finding.fix_type == 'circuit_breaker':
        checks.extend([
            check_fallback_defined(finding),
            check_fallback_tested(finding),
        ])

    return ValidationResult(
        passed=all(c.passed for c in checks),
        checks=checks
    )
```

---

## Manual Review Checklists

### Security Code Review

```markdown
## Security Review Checklist

### Input Handling
- [ ] All user input validated
- [ ] Input sanitized before use
- [ ] No eval() or equivalent with user input
- [ ] File paths validated and sandboxed

### Authentication
- [ ] Auth required where needed
- [ ] Session handled securely
- [ ] Password handling uses bcrypt/argon2
- [ ] No timing attacks in comparisons

### Authorization
- [ ] Access control enforced
- [ ] No IDOR vulnerabilities
- [ ] Principle of least privilege
- [ ] Admin functions protected

### Data Handling
- [ ] Sensitive data encrypted
- [ ] No PII in logs
- [ ] Proper error messages (no info leak)
- [ ] Secure defaults
```

### Architecture Review

```markdown
## Architecture Review Checklist

### Coupling
- [ ] No circular dependencies
- [ ] Interfaces at module boundaries
- [ ] Dependency direction correct (stable → unstable)
- [ ] No hidden dependencies

### Cohesion
- [ ] Single responsibility per class
- [ ] Related functionality grouped
- [ ] No god objects
- [ ] Clear module boundaries

### Patterns
- [ ] Consistent patterns used
- [ ] No anti-patterns introduced
- [ ] Domain model respected
- [ ] Error handling consistent
```

---

## Continuous Validation

### Post-Deployment Monitoring

```yaml
monitors:
  - name: error-rate
    query: rate(http_errors_total[5m]) / rate(http_requests_total[5m])
    threshold: 0.01
    alert_if: above

  - name: latency-p99
    query: histogram_quantile(0.99, http_request_duration_seconds)
    threshold: 2.0
    alert_if: above

  - name: circuit-breaker-opens
    query: increase(circuit_breaker_state{state="open"}[5m])
    threshold: 0
    alert_if: above
```

### Regression Detection

```yaml
regression_checks:
  - name: security-scan-weekly
    schedule: "0 0 * * 0"
    command: debt-audit --category security --baseline last_week
    alert_if: regression

  - name: coupling-metrics-weekly
    schedule: "0 0 * * 0"
    command: debt-audit --category coupling --baseline last_week
    alert_if: degraded
```

---

## Sign-Off Requirements

| Fix Type | Required Sign-Off |
|----------|-------------------|
| CRITICAL Security | Security team + Engineering lead |
| HIGH Security | Security-aware developer |
| Auth/AuthZ | Security team |
| Data/Privacy | Privacy/Legal review |
| Architecture | Tech lead |
| Other | Peer review |
