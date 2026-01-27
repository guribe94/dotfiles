# Safe Remediation Sequences

## Core Principle

**Never refactor untested code. Tests first, always.**

This document defines the safe order for addressing tech debt to minimize risk and maximize effectiveness.

---

## Master Sequence

```
1. CRITICAL Security Vulnerabilities (immediate)
   └─ Active exploits, credential exposure, injection flaws

2. Test Coverage for Affected Code
   └─ Cannot safely fix what you cannot verify

3. Resilience Fundamentals
   └─ Timeouts, circuit breakers, retries with backoff

4. Observability
   └─ Logging, metrics, tracing for visibility

5. Error Handling
   └─ Proper error boundaries, meaningful messages

6. Dependency Updates (security-first)
   └─ Patch vulnerabilities before features

7. Auth/AuthZ Hardening
   └─ Missing auth, access control, session security

8. Documentation
   └─ Runbooks, API docs, architecture decisions

9. Performance Optimization
   └─ Only after stability is assured

10. Architecture Refactoring
    └─ Coupling reduction, pattern fixes

11. Domain Model Improvements
    └─ Bounded contexts, aggregates

12. Legacy Migration
    └─ Strangler fig, adapters
```

---

## Why This Order?

### 1. Security First

Exploitable vulnerabilities take precedence because:
- Active risk of breach
- Compliance violations
- Legal liability
- Customer trust

### 2. Tests Before Fixes

You cannot safely fix code without tests because:
- No way to verify the fix works
- No way to prevent regressions
- No confidence in deployment
- Technical debt compounds

### 3. Resilience Before Features

System stability enables everything else:
- Cascading failures mask other issues
- Timeouts prevent resource exhaustion
- Circuit breakers contain failures
- Fallbacks maintain service

### 4. Observability Before Optimization

You cannot improve what you cannot measure:
- Logs reveal actual behavior
- Metrics show patterns
- Traces identify bottlenecks
- Alerts catch regressions

### 5. Dependencies Before Refactoring

Security patches cannot wait:
- Known CVEs are actively exploited
- Supply chain attacks are increasing
- Audit findings require response
- Compliance mandates timely patching

---

## Category-Specific Sequences

### Security Debt Sequence

```
1. Injection vulnerabilities (SQL, XSS, command)
   └─ Highest exploitability

2. Secrets exposure
   └─ Immediate credential risk

3. Authentication gaps
   └─ Unauthenticated access

4. Authorization flaws
   └─ IDOR, privilege escalation

5. Cryptographic weaknesses
   └─ Weak hashing, bad RNG

6. Session management
   └─ Fixation, storage

7. Security headers
   └─ CORS, CSP, HSTS

8. Supply chain
   └─ Vulnerable dependencies

9. Privacy/compliance
   └─ PII exposure, GDPR
```

### Operational Debt Sequence

```
1. Critical timeouts
   └─ Prevent cascading failures

2. Rate limiting
   └─ Prevent abuse, DoS

3. Health checks
   └─ Enable proper orchestration

4. Error handling
   └─ Graceful degradation

5. Logging gaps
   └─ Debug capability

6. Metrics instrumentation
   └─ Monitoring capability

7. Circuit breakers
   └─ Fault isolation

8. Alerting
   └─ Issue detection

9. Runbooks
   └─ Incident response
```

### Architecture Debt Sequence

```
1. Coupling metrics
   └─ Identify problem areas

2. Test coverage
   └─ Enable safe refactoring

3. Interface extraction
   └─ Reduce direct dependencies

4. SOLID violations (high-impact)
   └─ SRP for large classes

5. Anti-pattern removal
   └─ God objects first

6. Domain model fixes
   └─ Bounded context alignment

7. API contract cleanup
   └─ Versioning, deprecation

8. Event/async patterns
   └─ Saga compensation

9. Legacy migration
   └─ Strangler fig execution
```

---

## Dependency Graphs

### Security Dependencies

```
Secrets Exposure
└─ Must fix before: Auth improvements (need secure storage)

Injection Flaws
└─ Can fix independently

Auth Gaps
└─ Depends on: Secure session management
└─ Depends on: Proper crypto

Session Management
└─ Depends on: Crypto fixes (secure cookies)

Security Headers
└─ Can fix independently
└─ Often quick wins
```

### Resilience Dependencies

```
Timeouts
└─ Must add before: Retries, Circuit breakers

Retries
└─ Depends on: Timeouts (prevent infinite waits)
└─ Must implement: Exponential backoff + jitter

Circuit Breakers
└─ Depends on: Timeouts
└─ Depends on: Metrics (to know when to open)

Fallbacks
└─ Depends on: Circuit breakers (trigger fallback)
```

### Refactoring Dependencies

```
Test Coverage
└─ Must achieve before: Any refactoring

Interface Extraction
└─ Depends on: Test coverage
└─ Must do before: Dependency injection

God Object Split
└─ Depends on: Test coverage
└─ Depends on: Clear interface definitions

Coupling Reduction
└─ Depends on: Interface extraction
└─ Depends on: God object remediation
```

---

## Anti-Patterns to Avoid

### 1. Refactoring Without Tests

**Wrong:**
```
1. Identify god object
2. Split into smaller classes
3. Hope nothing broke
```

**Right:**
```
1. Identify god object
2. Add characterization tests
3. Achieve >80% coverage on affected code
4. Split with confidence
5. Verify tests still pass
```

### 2. Security After Features

**Wrong:**
```
Sprint 1: New feature
Sprint 2: Another feature
Sprint 3: "We'll add auth later"
Sprint 4: Security incident
```

**Right:**
```
Sprint 1: Security audit
Sprint 1: Fix CRITICAL issues
Sprint 2: New feature WITH proper auth
Sprint 2: Security review in PR
```

### 3. Optimizing Before Stabilizing

**Wrong:**
```
1. "The service is slow"
2. Add caching everywhere
3. Still have timeout issues
4. Cascading failures
```

**Right:**
```
1. Add timeouts first
2. Add circuit breakers
3. Add metrics
4. Identify actual bottleneck
5. Targeted optimization
```

### 4. Big Bang Refactoring

**Wrong:**
```
1. Rewrite entire module
2. One massive PR
3. Merge with fingers crossed
4. Production issues
5. Can't rollback (too much changed)
```

**Right:**
```
1. Add tests to existing code
2. Extract one interface
3. Migrate one consumer
4. Verify, repeat
5. Incremental, reversible progress
```

---

## Validation Checkpoints

Before moving to the next phase, verify:

### After Security Fixes

- [ ] All CRITICAL vulnerabilities addressed
- [ ] No secrets in codebase
- [ ] Auth on all sensitive endpoints
- [ ] Security scan passes
- [ ] Penetration test (if applicable)

### After Resilience Fixes

- [ ] All external calls have timeouts
- [ ] Retries use exponential backoff
- [ ] Circuit breakers on critical paths
- [ ] Fallbacks for non-critical features
- [ ] Chaos test passes

### After Observability

- [ ] Structured logging throughout
- [ ] Correlation IDs propagated
- [ ] RED metrics for all services
- [ ] Distributed traces connected
- [ ] Alerts have runbooks

### After Refactoring

- [ ] Test coverage maintained/improved
- [ ] No new lint errors
- [ ] Performance not degraded
- [ ] API contracts unchanged (or versioned)
- [ ] Documentation updated

---

## Time Boxing

To prevent analysis paralysis:

| Phase | Max Duration |
|-------|--------------|
| CRITICAL security | 1 week |
| Test coverage | 2 weeks per module |
| Resilience basics | 1 week |
| Per-category fixes | 1-2 sprints |

If a fix takes longer than expected:
1. Split into smaller pieces
2. Ship incremental progress
3. Create follow-up tickets
4. Don't block other work

---

## Rollback Strategy

Every remediation should have a rollback plan:

### Low-Risk Changes
- Feature flags
- Config changes
- Revert commit

### Medium-Risk Changes
- Blue/green deployment
- Canary release
- Database backward compatibility

### High-Risk Changes
- Shadow deployment
- Parallel running
- Gradual migration
- Full rollback tested
