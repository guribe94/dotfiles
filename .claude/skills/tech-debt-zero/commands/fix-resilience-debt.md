# /fix-resilience-debt

Fix missing timeouts, retries without backoff, absent circuit breakers, and fallback gaps.

## Usage

```
/fix-resilience-debt [path] [options]
```

### Options

- `--check <type>` - Focus on specific issue (timeouts, retries, circuit-breakers, fallbacks)
- `--dry-run` - Show what would be fixed without making changes

## Instructions

When the user runs `/fix-resilience-debt`:

1. **Run the resilience analyzer**:
   ```bash
   python ~/.claude/skills/tech-debt-zero/scripts/analyzers/analyze_resilience.py [path]
   ```

2. **For each finding, apply the appropriate fix**:

### Timeout Fixes

**HTTP Client Timeouts:**

```javascript
// Before (no timeout)
const response = await axios.get(url)
const data = await fetch(url)

// After (with timeout)
const response = await axios.get(url, { timeout: 5000 })

// fetch with AbortController
const controller = new AbortController()
const timeoutId = setTimeout(() => controller.abort(), 5000)
const data = await fetch(url, { signal: controller.signal })
clearTimeout(timeoutId)

// Or use fetch wrapper
async function fetchWithTimeout(url, options = {}, timeout = 5000) {
  const controller = new AbortController()
  const id = setTimeout(() => controller.abort(), timeout)

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal
    })
    return response
  } finally {
    clearTimeout(id)
  }
}
```

**Database Timeouts:**

```javascript
// PostgreSQL
const pool = new Pool({
  connectionTimeoutMillis: 5000,
  idleTimeoutMillis: 30000,
  query_timeout: 10000
})

// MongoDB
mongoose.connect(uri, {
  serverSelectionTimeoutMS: 5000,
  socketTimeoutMS: 45000
})

// Redis
const redis = new Redis({
  connectTimeout: 5000,
  commandTimeout: 3000
})
```

### Retry with Exponential Backoff

**Install retry library:**
```bash
npm install p-retry  # Node.js
pip install tenacity  # Python
```

**Node.js (p-retry):**
```javascript
const pRetry = require('p-retry')

async function fetchWithRetry(url) {
  return pRetry(
    async () => {
      const response = await fetch(url, { timeout: 5000 })
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      return response.json()
    },
    {
      retries: 3,
      onFailedAttempt: error => {
        console.log(`Attempt ${error.attemptNumber} failed. ${error.retriesLeft} retries left.`)
      },
      // Exponential backoff with jitter
      minTimeout: 1000,
      maxTimeout: 10000,
      randomize: true
    }
  )
}
```

**Python (tenacity):**
```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError))
)
def fetch_with_retry(url):
    response = requests.get(url, timeout=5)
    response.raise_for_status()
    return response.json()
```

### Circuit Breaker

**Install circuit breaker library:**
```bash
npm install opossum  # Node.js
pip install pybreaker  # Python
```

**Node.js (opossum):**
```javascript
const CircuitBreaker = require('opossum')

const options = {
  timeout: 3000,           // Trip after 3s
  errorThresholdPercentage: 50,  // Trip when 50% fail
  resetTimeout: 30000      // Try again after 30s
}

const breaker = new CircuitBreaker(callExternalService, options)

// Add fallback
breaker.fallback(() => {
  return { data: getCachedData(), source: 'cache', degraded: true }
})

// Add listeners
breaker.on('open', () => logger.warn('Circuit opened'))
breaker.on('halfOpen', () => logger.info('Circuit half-open'))
breaker.on('close', () => logger.info('Circuit closed'))

// Use it
async function getDataSafely() {
  return breaker.fire(serviceUrl)
}
```

**Python (pybreaker):**
```python
import pybreaker

db_breaker = pybreaker.CircuitBreaker(
    fail_max=5,
    reset_timeout=30,
    exclude=[pybreaker.CircuitBreakerError]
)

@db_breaker
def get_user(user_id):
    return db.query(f"SELECT * FROM users WHERE id = {user_id}")

# With fallback
def get_user_safe(user_id):
    try:
        return get_user(user_id)
    except pybreaker.CircuitBreakerError:
        return get_cached_user(user_id)
```

### Fallback Patterns

**Cached Fallback:**
```javascript
async function getRecommendations(userId) {
  try {
    return await recommendationService.getPersonalized(userId)
  } catch (error) {
    // Fallback to cached recommendations
    const cached = await cache.get(`recommendations:${userId}`)
    if (cached) {
      return { ...cached, source: 'cache', degraded: true }
    }

    // Fallback to popular items
    return {
      items: await getPopularItems(),
      source: 'popular',
      degraded: true
    }
  }
}
```

**Default Value Fallback:**
```javascript
async function getFeatureFlags(userId) {
  try {
    return await featureFlagService.get(userId)
  } catch (error) {
    logger.warn('Feature flag service unavailable, using defaults')
    return DEFAULT_FEATURE_FLAGS
  }
}
```

3. **Verify the fix**:
   - Test timeout behavior (mock slow responses)
   - Test retry behavior (mock failures)
   - Test circuit breaker (mock repeated failures)
   - Test fallback paths

## Remediation Checklist

### Timeouts
- [ ] All HTTP clients have timeout config
- [ ] Database connections have timeout
- [ ] Cache operations have timeout
- [ ] gRPC calls have deadlines
- [ ] Timeout values are reasonable (not too short/long)
- [ ] Timeout errors handled gracefully

### Retries
- [ ] Retries use exponential backoff
- [ ] Backoff includes jitter (randomization)
- [ ] Max retry count is bounded
- [ ] Only retryable errors are retried
- [ ] Non-idempotent operations not retried blindly

### Circuit Breakers
- [ ] External services wrapped in circuit breakers
- [ ] Thresholds configured appropriately
- [ ] Half-open state tested
- [ ] Fallbacks defined for open state
- [ ] Circuit state monitored/alerted

### Fallbacks
- [ ] Critical operations have fallback paths
- [ ] Fallback data clearly marked as degraded
- [ ] Fallback behavior tested

## Recommended Timeout Values

| Operation | Timeout |
|-----------|---------|
| Database query | 5-30s |
| HTTP API call | 3-10s |
| Cache lookup | 100-500ms |
| Internal service | 1-5s |
| External API | 10-30s |
| File operation | 5-60s |

## References

- Netflix Hystrix patterns
- AWS Well-Architected - Reliability Pillar
- Release It! by Michael Nygard
