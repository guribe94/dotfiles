# Resilience Patterns

Patterns for building fault-tolerant distributed systems.

---

## Timeouts

### Why Timeouts Matter

Without timeouts:
- Resources exhausted waiting for unresponsive services
- Cascading failures across system
- User experience degrades unpredictably
- Recovery becomes impossible

### Implementation

```javascript
// HTTP client timeout
const axios = require('axios');

const client = axios.create({
  timeout: 5000,  // 5 seconds
  timeoutErrorMessage: 'Request timed out'
});

// Or per-request
await axios.get(url, { timeout: 3000 });
```

```javascript
// Database timeout
const pool = new Pool({
  connectionTimeoutMillis: 5000,
  idleTimeoutMillis: 30000,
  query_timeout: 10000
});

// Query-level timeout
await pool.query('SELECT ...', { timeout: 5000 });
```

```javascript
// Generic promise timeout
function withTimeout(promise, ms) {
  const timeout = new Promise((_, reject) =>
    setTimeout(() => reject(new Error('Timeout')), ms)
  );
  return Promise.race([promise, timeout]);
}

await withTimeout(slowOperation(), 5000);
```

### Timeout Guidelines

| Operation | Recommended Timeout |
|-----------|---------------------|
| Database query | 5-30 seconds |
| HTTP API call | 3-10 seconds |
| Cache lookup | 100-500 ms |
| Internal service | 1-5 seconds |
| External API | 10-30 seconds |
| File operation | 5-60 seconds |

---

## Retries with Exponential Backoff

### Why Backoff Matters

Without backoff:
- Thundering herd overwhelms recovering service
- Resources wasted on futile retries
- Recovery delayed or prevented

### Implementation

```javascript
async function retryWithBackoff(fn, options = {}) {
  const {
    maxRetries = 3,
    baseDelay = 1000,
    maxDelay = 30000,
    jitter = true,
    retryOn = () => true
  } = options;

  let lastError;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;

      if (attempt === maxRetries || !retryOn(error)) {
        throw error;
      }

      // Exponential backoff with jitter
      let delay = Math.min(baseDelay * Math.pow(2, attempt), maxDelay);
      if (jitter) {
        delay = delay * (0.5 + Math.random());  // 50-150% of calculated delay
      }

      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }

  throw lastError;
}

// Usage
const result = await retryWithBackoff(
  () => axios.get(url),
  {
    maxRetries: 3,
    baseDelay: 1000,
    retryOn: (err) => err.response?.status >= 500 || err.code === 'ECONNRESET'
  }
);
```

### Retry Guidelines

**Retry:**
- 5xx server errors
- Network timeouts
- Connection resets
- Rate limiting (with appropriate delay)

**Don't Retry:**
- 4xx client errors (except 429)
- Authentication failures
- Validation errors
- Business logic errors

---

## Circuit Breaker

### States

```
CLOSED (normal) → OPEN (failing) → HALF-OPEN (testing) → CLOSED
       ↑                                    │
       └────────────────────────────────────┘
```

### Implementation

```javascript
class CircuitBreaker {
  constructor(options = {}) {
    this.failureThreshold = options.failureThreshold || 5;
    this.resetTimeout = options.resetTimeout || 30000;
    this.halfOpenRequests = options.halfOpenRequests || 1;

    this.state = 'CLOSED';
    this.failures = 0;
    this.successes = 0;
    this.lastFailure = null;
    this.halfOpenCount = 0;
  }

  async execute(fn) {
    if (this.state === 'OPEN') {
      if (Date.now() - this.lastFailure > this.resetTimeout) {
        this.state = 'HALF_OPEN';
        this.halfOpenCount = 0;
      } else {
        throw new Error('Circuit breaker is OPEN');
      }
    }

    if (this.state === 'HALF_OPEN' && this.halfOpenCount >= this.halfOpenRequests) {
      throw new Error('Circuit breaker is HALF_OPEN, waiting for test requests');
    }

    try {
      if (this.state === 'HALF_OPEN') {
        this.halfOpenCount++;
      }

      const result = await fn();

      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  onSuccess() {
    if (this.state === 'HALF_OPEN') {
      this.successes++;
      if (this.successes >= this.halfOpenRequests) {
        this.state = 'CLOSED';
        this.failures = 0;
        this.successes = 0;
      }
    } else {
      this.failures = 0;
    }
  }

  onFailure() {
    this.failures++;
    this.lastFailure = Date.now();

    if (this.state === 'HALF_OPEN' || this.failures >= this.failureThreshold) {
      this.state = 'OPEN';
    }
  }
}

// Usage
const breaker = new CircuitBreaker({
  failureThreshold: 5,
  resetTimeout: 30000
});

try {
  const result = await breaker.execute(() => axios.get(url));
} catch (error) {
  if (error.message.includes('Circuit breaker')) {
    // Use fallback
    return fallbackValue;
  }
  throw error;
}
```

### Using Libraries

```javascript
// opossum (Node.js)
const CircuitBreaker = require('opossum');

const breaker = new CircuitBreaker(asyncFunction, {
  timeout: 3000,
  errorThresholdPercentage: 50,
  resetTimeout: 30000
});

breaker.fallback(() => fallbackValue);
breaker.on('open', () => console.log('Circuit opened'));
breaker.on('halfOpen', () => console.log('Circuit half-open'));
breaker.on('close', () => console.log('Circuit closed'));

const result = await breaker.fire(args);
```

---

## Fallbacks

### Fallback Strategies

| Strategy | Use Case | Example |
|----------|----------|---------|
| **Cache** | Read operations | Return cached data |
| **Default** | Non-critical data | Return default values |
| **Degraded** | Feature reduction | Disable non-essential features |
| **Queue** | Write operations | Queue for later processing |
| **Alternative** | Redundant services | Try backup service |

### Implementation

```javascript
async function getRecommendations(userId) {
  const breaker = getCircuitBreaker('recommendations');

  try {
    // Primary: ML-powered recommendations
    return await breaker.execute(() =>
      recommendationService.getPersonalized(userId)
    );
  } catch (error) {
    // Fallback 1: Cached recommendations
    const cached = await cache.get(`recommendations:${userId}`);
    if (cached) {
      return { ...cached, source: 'cache' };
    }

    // Fallback 2: Popular items (degraded)
    const popular = await getPopularItems();
    return { items: popular, source: 'popular', degraded: true };
  }
}
```

### Fallback Guidelines

1. **Always have a fallback** for non-critical features
2. **Indicate degradation** to callers/users
3. **Monitor fallback usage** (indicates problems)
4. **Test fallbacks** regularly
5. **Don't cascade fallbacks** indefinitely

---

## Bulkhead

### Why Bulkheads Matter

Without bulkheads:
- One slow dependency exhausts all resources
- System-wide failure from localized issue
- No isolation between components

### Thread Pool Isolation

```javascript
// Separate thread pools per dependency
const paymentPool = new Pool({ max: 10 });
const inventoryPool = new Pool({ max: 10 });
const notificationPool = new Pool({ max: 5 });

// Each pool isolated - payment issues don't affect inventory
async function processOrder(order) {
  const [payment, inventory] = await Promise.all([
    paymentPool.execute(() => processPayment(order)),
    inventoryPool.execute(() => reserveInventory(order))
  ]);

  // Notification is non-critical, separate pool
  notificationPool.execute(() => sendConfirmation(order))
    .catch(err => log.warn('Notification failed', err));

  return { payment, inventory };
}
```

### Semaphore-Based Bulkhead

```javascript
class Semaphore {
  constructor(max) {
    this.max = max;
    this.current = 0;
    this.queue = [];
  }

  async acquire() {
    if (this.current < this.max) {
      this.current++;
      return;
    }

    return new Promise(resolve => {
      this.queue.push(resolve);
    });
  }

  release() {
    this.current--;
    if (this.queue.length > 0) {
      this.current++;
      const next = this.queue.shift();
      next();
    }
  }

  async execute(fn) {
    await this.acquire();
    try {
      return await fn();
    } finally {
      this.release();
    }
  }
}

// Usage
const externalApiSemaphore = new Semaphore(10);  // Max 10 concurrent

async function callExternalApi() {
  return externalApiSemaphore.execute(async () => {
    return await axios.get(externalUrl);
  });
}
```

---

## Rate Limiting

### Client-Side Rate Limiting

```javascript
class RateLimiter {
  constructor(maxRequests, windowMs) {
    this.maxRequests = maxRequests;
    this.windowMs = windowMs;
    this.requests = [];
  }

  async acquire() {
    const now = Date.now();
    this.requests = this.requests.filter(t => now - t < this.windowMs);

    if (this.requests.length >= this.maxRequests) {
      const oldestRequest = this.requests[0];
      const waitTime = this.windowMs - (now - oldestRequest);
      await new Promise(resolve => setTimeout(resolve, waitTime));
      return this.acquire();
    }

    this.requests.push(now);
  }
}

const limiter = new RateLimiter(100, 60000);  // 100 requests per minute

async function callApi() {
  await limiter.acquire();
  return await axios.get(url);
}
```

### Server-Side Rate Limiting

```javascript
const rateLimit = require('express-rate-limit');

// General API rate limit
app.use('/api/', rateLimit({
  windowMs: 15 * 60 * 1000,  // 15 minutes
  max: 100,
  message: { error: 'Too many requests' }
}));

// Stricter limit for auth endpoints
app.use('/api/auth/', rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 5,
  message: { error: 'Too many login attempts' }
}));
```

---

## Load Shedding

### When to Shed Load

- CPU > 90%
- Memory > 90%
- Queue depth > threshold
- Response time > SLO

### Implementation

```javascript
// Middleware for load shedding
function loadSheddingMiddleware(options = {}) {
  const { maxQueueDepth = 100, maxLatency = 1000 } = options;
  let queueDepth = 0;
  let avgLatency = 0;

  return async (req, res, next) => {
    // Check if we should shed
    if (queueDepth > maxQueueDepth || avgLatency > maxLatency) {
      res.status(503).json({
        error: 'Service temporarily unavailable',
        retryAfter: 5
      });
      return;
    }

    queueDepth++;
    const start = Date.now();

    res.on('finish', () => {
      queueDepth--;
      const latency = Date.now() - start;
      avgLatency = avgLatency * 0.9 + latency * 0.1;  // Exponential moving average
    });

    next();
  };
}
```

---

## Health Check Patterns

### Deep Health Check

```javascript
app.get('/health/deep', async (req, res) => {
  const checks = {};

  // Database
  try {
    await db.query('SELECT 1');
    checks.database = { status: 'healthy', latency: Date.now() - start };
  } catch (error) {
    checks.database = { status: 'unhealthy', error: error.message };
  }

  // Cache
  try {
    await cache.ping();
    checks.cache = { status: 'healthy' };
  } catch (error) {
    checks.cache = { status: 'unhealthy', error: error.message };
  }

  // External service
  try {
    await axios.get(`${externalService}/health`, { timeout: 2000 });
    checks.externalService = { status: 'healthy' };
  } catch (error) {
    checks.externalService = { status: 'unhealthy', error: error.message };
  }

  const allHealthy = Object.values(checks).every(c => c.status === 'healthy');

  res.status(allHealthy ? 200 : 503).json({
    status: allHealthy ? 'healthy' : 'unhealthy',
    timestamp: new Date().toISOString(),
    checks
  });
});
```

---

## Chaos Engineering

### Principles

1. Start with steady state hypothesis
2. Vary real-world events
3. Run in production
4. Automate experiments
5. Minimize blast radius

### Simple Chaos Injection

```javascript
// Chaos middleware for testing
function chaosMiddleware(options = {}) {
  const { latencyMs = 0, failureRate = 0, enabled = false } = options;

  return (req, res, next) => {
    if (!enabled) return next();

    // Inject latency
    if (latencyMs > 0) {
      const delay = Math.random() * latencyMs;
      setTimeout(next, delay);
      return;
    }

    // Inject failures
    if (Math.random() < failureRate) {
      res.status(500).json({ error: 'Chaos injection' });
      return;
    }

    next();
  };
}

// Only enable in test environments
if (process.env.ENABLE_CHAOS === 'true') {
  app.use(chaosMiddleware({
    enabled: true,
    latencyMs: 500,
    failureRate: 0.1
  }));
}
```
