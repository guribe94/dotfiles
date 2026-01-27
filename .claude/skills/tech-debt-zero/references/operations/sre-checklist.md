# SRE Checklist

Site Reliability Engineering standards for production systems.

---

## Service Level Objectives

### SLI Definition

| SLI Type | Formula | Example |
|----------|---------|---------|
| **Availability** | Successful requests / Total requests | 99.9% |
| **Latency** | Requests < threshold / Total requests | 95% < 200ms |
| **Throughput** | Requests processed / Time window | 1000 req/s |
| **Error Rate** | Failed requests / Total requests | < 0.1% |

### SLO Requirements

- [ ] SLIs defined for all critical services
- [ ] SLOs documented and agreed upon
- [ ] Error budgets calculated
- [ ] Burn rate alerts configured
- [ ] SLO review cadence established

### Error Budget Calculation

```
Error Budget = 1 - SLO

Example:
SLO = 99.9% availability
Error Budget = 0.1% = 43.2 minutes/month downtime allowed

Monthly budget: 43.2 minutes
Weekly budget: ~10 minutes
Daily budget: ~1.4 minutes
```

### Multi-Window Alerting

```yaml
# Fast burn (high severity)
- alert: ErrorBudgetBurnHigh
  expr: |
    (
      sum(rate(http_requests_total{status=~"5.."}[1h]))
      /
      sum(rate(http_requests_total[1h]))
    ) > (14.4 * 0.001)  # 14.4x burn rate
  for: 2m
  labels:
    severity: critical

# Slow burn (warning)
- alert: ErrorBudgetBurnSlow
  expr: |
    (
      sum(rate(http_requests_total{status=~"5.."}[6h]))
      /
      sum(rate(http_requests_total[6h]))
    ) > (1 * 0.001)  # 1x burn rate
  for: 1h
  labels:
    severity: warning
```

---

## Health Checks

### Liveness Probe

Determines if the application is running. Failed = restart container.

```javascript
app.get('/health/live', (req, res) => {
  // Only check if process is alive
  // NOT external dependencies
  res.status(200).json({ status: 'alive' });
});
```

```yaml
# Kubernetes
livenessProbe:
  httpGet:
    path: /health/live
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 10
  failureThreshold: 3
```

### Readiness Probe

Determines if the application can receive traffic. Failed = remove from load balancer.

```javascript
app.get('/health/ready', async (req, res) => {
  const checks = {
    database: await checkDatabase(),
    cache: await checkCache(),
    dependencies: await checkDependencies()
  };

  const allHealthy = Object.values(checks).every(c => c.healthy);

  res.status(allHealthy ? 200 : 503).json({
    status: allHealthy ? 'ready' : 'not_ready',
    checks
  });
});
```

```yaml
# Kubernetes
readinessProbe:
  httpGet:
    path: /health/ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
  failureThreshold: 3
```

### Startup Probe

For slow-starting applications. Prevents liveness probe from killing during startup.

```yaml
startupProbe:
  httpGet:
    path: /health/live
    port: 8080
  failureThreshold: 30
  periodSeconds: 10  # 5 minute max startup
```

---

## Monitoring

### RED Method (Request-driven)

For every service, track:

| Metric | What | Prometheus Example |
|--------|------|-------------------|
| **Rate** | Requests per second | `rate(http_requests_total[5m])` |
| **Errors** | Failed requests per second | `rate(http_requests_total{status=~"5.."}[5m])` |
| **Duration** | Latency distribution | `histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))` |

### USE Method (Resource-driven)

For every resource (CPU, memory, disk, network):

| Metric | What | Example |
|--------|------|---------|
| **Utilization** | % time resource is busy | CPU usage % |
| **Saturation** | Queue depth | Memory pressure |
| **Errors** | Error events | Disk errors |

### Four Golden Signals

1. **Latency** - Time to service a request
2. **Traffic** - Demand on the system
3. **Errors** - Rate of failed requests
4. **Saturation** - How "full" the service is

### Implementation Checklist

- [ ] RED metrics for all services
- [ ] USE metrics for all infrastructure
- [ ] Dashboards per service
- [ ] Latency percentiles (p50, p95, p99)
- [ ] Error rate by type
- [ ] Dependency health visibility

---

## Alerting

### Alert Quality Requirements

- [ ] Actionable (requires human intervention)
- [ ] Has runbook linked
- [ ] Clear ownership
- [ ] Appropriate severity
- [ ] Tested regularly

### Alert Template

```yaml
- alert: HighErrorRate
  expr: |
    sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)
    /
    sum(rate(http_requests_total[5m])) by (service)
    > 0.05
  for: 5m
  labels:
    severity: critical
    team: platform
  annotations:
    summary: "High error rate on {{ $labels.service }}"
    description: "Error rate is {{ $value | humanizePercentage }} (>5%)"
    runbook: "https://runbooks.example.com/high-error-rate"
    dashboard: "https://grafana.example.com/d/service/{{ $labels.service }}"
```

### Severity Levels

| Severity | Response Time | Example |
|----------|---------------|---------|
| **Critical** | Immediate (page) | Service down, data loss risk |
| **High** | 30 minutes | Significant degradation |
| **Medium** | 4 hours | Minor degradation |
| **Low** | Next business day | Performance issue |

### Alert Anti-Patterns

**Avoid:**
- Alerts without runbooks
- Alerts that don't require action
- Low-signal, high-noise alerts
- Alerts on metrics, not symptoms
- Missing context in alert messages

---

## Incident Management

### Severity Classification

| Severity | Impact | Example |
|----------|--------|---------|
| **SEV1** | Complete outage, data loss | Production down |
| **SEV2** | Major feature unavailable | Payments failing |
| **SEV3** | Minor feature unavailable | Search slow |
| **SEV4** | Minimal impact | Dashboard widget broken |

### Incident Response Checklist

- [ ] Incident declared and severity set
- [ ] Incident commander assigned
- [ ] Communication channel established
- [ ] Status page updated
- [ ] Relevant teams engaged
- [ ] Customer communication sent (if needed)
- [ ] Root cause identified
- [ ] Fix deployed
- [ ] Post-incident review scheduled

### Post-Incident Review

```markdown
## Incident Review: [Title]

### Timeline
- HH:MM - First alert fired
- HH:MM - Incident declared
- HH:MM - Root cause identified
- HH:MM - Fix deployed
- HH:MM - Service restored

### Impact
- Duration: X hours
- Users affected: Y
- Revenue impact: $Z

### Root Cause
[Description of what caused the incident]

### Contributing Factors
- Factor 1
- Factor 2

### Action Items
- [ ] AI-001: [Action] - Owner - Due date
- [ ] AI-002: [Action] - Owner - Due date

### Lessons Learned
- What went well
- What could be improved
```

---

## Capacity Planning

### Metrics to Track

- Current resource utilization
- Growth rate
- Seasonal patterns
- Headroom requirements

### Capacity Model

```
Required Capacity = (Current Usage × Growth Factor) + Headroom

Example:
Current CPU: 40%
Monthly growth: 5%
Planning horizon: 6 months
Growth factor: 1.05^6 = 1.34
Required capacity with 30% headroom: 40% × 1.34 + 30% = 83.6%
Action: Plan capacity increase
```

### Checklist

- [ ] Resource utilization dashboards
- [ ] Growth trend analysis
- [ ] Seasonal pattern identification
- [ ] Lead time for capacity changes known
- [ ] Capacity reviews scheduled quarterly

---

## Change Management

### Change Categories

| Category | Risk | Approval | Example |
|----------|------|----------|---------|
| **Standard** | Low | Pre-approved | Config update |
| **Normal** | Medium | CAB review | New feature |
| **Emergency** | High | Expedited | Security patch |

### Deployment Checklist

Pre-deployment:
- [ ] Tests passing
- [ ] Change reviewed
- [ ] Rollback plan documented
- [ ] Monitoring ready
- [ ] Communication sent

Post-deployment:
- [ ] Smoke tests passing
- [ ] Metrics nominal
- [ ] No error spike
- [ ] Communication sent

### Rollback Criteria

Automatically rollback if:
- Error rate > 5% for 2 minutes
- Latency p99 > 2× baseline for 5 minutes
- Health checks failing
- Critical alert firing

---

## Disaster Recovery

### RTO/RPO Definitions

- **RTO (Recovery Time Objective)**: Max acceptable downtime
- **RPO (Recovery Point Objective)**: Max acceptable data loss

### DR Tiers

| Tier | RTO | RPO | Strategy |
|------|-----|-----|----------|
| **1** | < 1 hour | 0 | Active-active |
| **2** | < 4 hours | < 1 hour | Hot standby |
| **3** | < 24 hours | < 24 hours | Warm standby |
| **4** | < 72 hours | < 72 hours | Cold backup |

### DR Checklist

- [ ] RTO/RPO defined per service
- [ ] Backup strategy implemented
- [ ] Recovery procedures documented
- [ ] DR tests scheduled (quarterly minimum)
- [ ] Cross-region replication where needed
- [ ] Failover automation tested

---

## Toil Reduction

### Toil Identification

Toil is:
- Manual
- Repetitive
- Automatable
- Tactical
- No enduring value
- Scales with service growth

### Toil Budget

- **Target**: < 50% of engineering time on toil
- **Track**: Time spent on toil vs. engineering work
- **Automate**: High-frequency toil first

### Automation Priorities

1. Incident response automation
2. Deployment automation
3. Capacity management automation
4. Configuration management automation
5. Testing automation
