# tech-debt-zero

Zero compromises. Everything addressed. Nothing left for later.

Expert-reviewed comprehensive technical debt elimination covering security, operations, architecture, and code quality. Exceeds SonarQube, Snyk, Codecov, and industry tools combined.

## Commands

### Core Commands

- `/debt-audit` - Complete 27-category scan with parallel analyzers. Detects security vulnerabilities, operational gaps, and architectural anti-patterns.
- `/debt-prioritize` - ROI-based ranking with exploitability/exposure factors. Calculates impact × effort for prioritized remediation.
- `/debt-track` - Progress tracking with trend analysis. Monitors debt reduction over time.
- `/debt-prevent` - Quality gates for CI/CD. Generates pre-commit hooks and pipeline checks.

### Security Commands (9)

- `/fix-injection-debt` - Fix SQL, XSS, command, SSRF, path traversal, NoSQL, XXE injection vulnerabilities.
- `/fix-crypto-debt` - Fix weak algorithms, hardcoded keys, insecure RNG issues.
- `/fix-session-debt` - Fix session fixation, insecure storage, cookie issues, missing timeout.
- `/fix-auth-debt` - Fix route auth gaps, IDOR, JWT vulnerabilities, access control issues.
- `/fix-headers-debt` - Fix CORS, CSP, HSTS, X-Frame-Options misconfigurations.
- `/fix-supply-chain-debt` - Fix vulnerable deps, typosquatting, lockfile integrity issues.
- `/fix-secrets-debt` - Fix hardcoded secrets, rotation gaps, exposure in logs/artifacts.
- `/fix-privacy-debt` - Fix PII detection, GDPR gaps, missing encryption.
- `/fix-infra-security-debt` - Fix IaC misconfigs, IAM, containers, K8s security.

### Operational Commands (9)

- `/fix-observability-debt` - Fix logging gaps, metrics, tracing, correlation IDs.
- `/fix-resilience-debt` - Fix missing timeouts, retries, circuit breakers, fallbacks.
- `/fix-deployment-debt` - Fix rollback capability, feature flags, zero-downtime support.
- `/fix-config-debt` - Fix hardcoded values, env-specific code, config drift.
- `/fix-slo-debt` - Fix SLIs, SLOs, health checks, error budgets.
- `/fix-alerting-debt` - Fix alert quality, fatigue, ownership, runbook links.
- `/fix-runbook-debt` - Fix documentation coverage, escalation paths.
- `/fix-build-debt` - Fix pipeline speed, flaky tests, quality gates.
- `/fix-rate-limit-debt` - Fix rate limiting on auth/API endpoints.

### Architecture Commands (9)

- `/fix-solid-debt` - Fix SOLID principle violations.
- `/fix-coupling-debt` - Fix high coupling, low cohesion, instability issues.
- `/fix-antipattern-debt` - Fix God object, anemic domain, feature envy patterns.
- `/fix-domain-debt` - Fix bounded context bleeding, aggregate violations.
- `/fix-api-contract-debt` - Fix breaking changes, versioning, deprecation gaps.
- `/fix-schema-debt` - Fix migration gaps, missing indexes, constraints.
- `/fix-distributed-debt` - Fix service coupling, data consistency issues.
- `/fix-event-debt` - Fix event versioning, saga compensation, DLQ handling.
- `/fix-legacy-debt` - Fix missing adapters, strangler fig violations, tech fragmentation.

## Debt Taxonomy (27 Categories)

### Security Debt (9)
1. Injection Vulnerabilities - SQL, XSS, command, LDAP, NoSQL, XXE, SSRF, path traversal
2. Cryptographic Weaknesses - Weak hashing, hardcoded keys, Math.random(), missing bcrypt
3. Session Management - Fixation, insecure storage, missing HttpOnly/Secure
4. Auth/AuthZ Gaps - Missing auth, IDOR, JWT vulnerabilities, broken access control
5. Security Headers - CORS, CSP, HSTS, X-Frame-Options, referrer policy
6. Supply Chain - Typosquatting, dependency confusion, vulnerable deps, lockfile integrity
7. Secrets Management - Hardcoded secrets, secrets in logs, missing rotation
8. Data Privacy - PII exposure, GDPR gaps, missing encryption
9. Infrastructure Security - IaC misconfigs, overly permissive IAM, container security

### Operational Debt (9)
10. Observability - Logging gaps, unstructured logs, missing correlation IDs
11. Resilience - Missing timeouts, retries without backoff, no circuit breakers
12. Deployment - No rollback capability, missing feature flags, irreversible migrations
13. Configuration - Hardcoded config, environment-specific code, config drift
14. SLO/Reliability - Missing SLIs/SLOs, no error budgets, missing health checks
15. Alerting - Alerts without runbooks, alert fatigue, missing critical alerts
16. Runbooks - Missing documentation, stale runbooks, incomplete escalation
17. Build/CI - Slow builds, flaky tests, missing quality gates
18. Rate Limiting - Missing rate limits on auth/API, brute force exposure

### Architectural Debt (9)
19. SOLID Violations - Single responsibility, open/closed, Liskov, ISP, DIP
20. Coupling/Cohesion - High coupling (Ca/Ce), low cohesion (LCOM), instability
21. Design Anti-Patterns - God object, anemic domain, feature envy, primitive obsession
22. Domain Model - Bounded context bleeding, anti-corruption layer absence
23. API Contract - Breaking changes, missing versioning, no deprecation notices
24. Schema Evolution - Migration gaps, backward-incompatible changes, missing indexes
25. Distributed Systems - Distributed monolith, chatty services, data consistency gaps
26. Event/Async - Event schema versioning, saga compensation, DLQ handling
27. Legacy Integration - Missing adapters, strangler fig violations, tech fragmentation

## Safe Remediation Sequence

1. CRITICAL security (immediate)
2. Add tests to untested code
3. Fix resilience (timeouts, circuit breakers)
4. Fix observability (logging, metrics)
5. Fix error handling
6. Update dependencies (security first)
7. Fix auth/authz gaps
8. Documentation
9. Performance optimization
10. Architecture refactoring
11. Coupling reduction
12. Legacy migration

**Key Principle**: Never refactor untested code. Tests first, always.
