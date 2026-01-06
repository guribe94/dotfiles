# Expert Review

Conduct a rigorous, critical review of the current work. Surface real issues with evidence—not generic advice. Focus on changed files and the surrounding context they affect.

**Core principle: No deferrals.** Every issue found must be addressed now. No "fix later" TODOs, no tech debt accepted, no hacky workarounds. If something isn't right, we fix it before moving on.

$ARGUMENTS

## Phase 1: Meta-Analysis

Before diving into details, answer:

1. **Right problem?** Are we solving the root cause or papering over a symptom?
2. **Simpler approach?** Is there a less complex solution we missed?
3. **Complete solution?** Are we handling all cases, or just the happy path?
4. **Pattern match?** Does this follow existing codebase conventions, or introduce a new pattern? If new, is that justified?
5. **Blast radius?** What's the worst-case failure scenario in production?
6. **Reversibility?** How do we roll back if this goes wrong? Is rollback safe?
7. **Dependencies?** Any new dependencies? Are they audited, maintained, necessary?

## Phase 2: Anti-Pattern Scan

Flag any of these immediately:
- `TODO`, `FIXME`, `HACK`, `XXX`, `TEMP`, `WORKAROUND` comments
- Commented-out code
- Magic numbers or hardcoded values that should be configured
- Copy-pasted code (DRY violations)
- Swallowed errors or empty catch blocks
- Any "we'll fix this later" patterns
- Shortcuts taken due to time pressure
- Features half-implemented or behind incomplete flags
- Dead code paths
- Inconsistent naming or conventions

**These must be resolved, not documented.**

## Phase 3: Expert Perspectives

### Security Engineer
- Injection vectors (SQL, command, path traversal, XSS, SSTI)
- Auth/authz gaps, privilege escalation, IDOR
- Data exposure, secrets in code/logs, PII leakage
- Input validation at trust boundaries
- Cryptographic choices (algorithms, randomness, key management)
- Dependency vulnerabilities (new deps especially)
- OWASP Top 10 relevance
- Session handling and CSRF protection
- Rate limiting and abuse prevention

### Performance Engineer
- Hot paths and critical sections
- N+1 queries, chatty APIs, unnecessary allocations
- Missing indexes, full table scans, query plan analysis
- Caching opportunities and invalidation correctness
- Resource leaks (connections, file handles, memory, goroutines)
- Scalability under 10x/100x load
- Timeout and backpressure handling
- Pagination for unbounded results
- Lazy loading vs eager loading tradeoffs

### Concurrency Specialist
- Race conditions and data races
- Deadlock potential (lock ordering)
- Atomicity violations (check-then-act, read-modify-write)
- Shared mutable state across threads/requests
- Idempotency of operations (safe to retry?)
- Transaction isolation and consistency
- Concurrent collection usage
- Signal handling and graceful shutdown

### Senior Architect
- Coupling between components (would changes cascade?)
- Abstraction quality (leaky? wrong level?)
- SOLID violations, especially SRP and DIP
- API contract clarity, stability, and versioning
- Error handling consistency (strategy matches codebase?)
- Configuration management (magic numbers, environment handling)
- Boundary clarity (where does this responsibility belong?)
- Interface segregation (are interfaces focused?)

### Data Engineer
- Schema change safety (backwards compatible?)
- Migration strategy (zero-downtime? reversible?)
- Data integrity constraints (foreign keys, unique, not null)
- Audit trail for sensitive operations
- Data retention and compliance (GDPR, PII handling)
- Consistency model appropriate for use case
- Backup and recovery implications
- Index strategy for query patterns

### QA Lead
- Test coverage: unit tests for all logic branches
- Test coverage: integration tests for component interactions
- Test coverage: e2e tests for critical user paths
- Edge cases: nulls, empty collections, boundaries, unicode, timezones, leap years
- Error path testing (failures, timeouts, partial failures, retries)
- Regression risk from changes
- Test isolation and determinism (no flaky tests)
- Contract/API tests for interfaces
- Mocking strategy (not over-mocked, testing real behavior)

### SRE/Ops Engineer
- Failure modes and recovery paths
- Observability: structured logging with correlation IDs
- Observability: metrics for business and technical KPIs
- Observability: distributed tracing integration
- Health checks and readiness signals
- Graceful degradation under partial failure
- Deployment safety (feature flags, gradual rollout, canary)
- Circuit breakers for external dependencies
- Alerting: actionable alerts with runbook links
- Documentation: what would on-call need to know?

### Cost Analyst
- Cloud resource implications (compute, storage, egress)
- API call volume to paid services
- Database growth trajectory
- Caching cost vs compute tradeoff
- Runaway cost scenarios (what if input is 1000x expected?)
- Resource cleanup (are we deleting what we create?)

## Phase 4: Completeness Check

Verify nothing is left incomplete:
- [ ] All error cases handled (not just logged, actually handled)
- [ ] All edge cases covered with tests
- [ ] All public interfaces documented
- [ ] All configuration externalized appropriately
- [ ] All new dependencies justified and audited
- [ ] All database changes have migrations
- [ ] All breaking changes have migration path
- [ ] All security-sensitive operations logged
- [ ] All user-facing errors are clear and actionable
- [ ] No orphaned code or partial implementations

## Phase 5: Findings

For each issue found:

| Severity | Location | Issue | Required Fix |
|----------|----------|-------|--------------|
| critical/high/medium/low | file:line | What's wrong + why it matters | Concrete remediation (mandatory) |

**Severity guide:**
- **Critical**: Security vulnerability, data loss/corruption risk, or correctness bug
- **High**: Significant bug, performance problem, or missing error handling
- **Medium**: Code quality issue, missing test coverage, or unclear code
- **Low**: Naming, style, minor improvements to clarity

**All findings must be addressed. No severity is acceptable to skip.**

## Phase 6: Verification Plan

1. **Pre-deploy checklist**: Specific manual verifications before deploying
2. **Post-deploy monitoring**: Metrics/logs to watch, expected values, duration
3. **Rollback trigger**: Specific conditions that should trigger rollback
4. **Success criteria**: How do we know this is working correctly?

## Phase 7: Final Verdict

- **PASS**: No issues remain. Ready to ship.
- **FAIL**: List every issue that must be resolved. Do not proceed until all are fixed.

If FAIL, work through each issue systematically until PASS is achieved.
