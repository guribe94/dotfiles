# Observability Standards

Standards for logging, metrics, and distributed tracing.

---

## Logging

### Structured Logging Format

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "service": "user-service",
  "version": "1.2.3",
  "environment": "production",
  "trace_id": "abc123",
  "span_id": "def456",
  "message": "User login successful",
  "user_id": "usr_123",
  "duration_ms": 45,
  "metadata": {
    "ip": "192.168.1.1",
    "user_agent": "Mozilla/5.0..."
  }
}
```

### Log Levels

| Level | Use Case | Example |
|-------|----------|---------|
| **ERROR** | Failures requiring attention | Database connection failed |
| **WARN** | Potentially harmful situations | Retry attempt, deprecation |
| **INFO** | Normal operations | Request completed, user action |
| **DEBUG** | Detailed debugging | Variable values, flow decisions |
| **TRACE** | Very detailed debugging | Function entry/exit |

### Implementation

```javascript
const winston = require('winston');

const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  defaultMeta: {
    service: process.env.SERVICE_NAME,
    version: process.env.VERSION,
    environment: process.env.NODE_ENV
  },
  transports: [
    new winston.transports.Console()
  ]
});

// Add correlation ID middleware
function correlationMiddleware(req, res, next) {
  const correlationId = req.headers['x-correlation-id'] || uuid();
  req.correlationId = correlationId;
  res.setHeader('x-correlation-id', correlationId);

  // Add to async context
  req.logger = logger.child({ correlation_id: correlationId });

  next();
}

// Usage
app.post('/api/users', async (req, res) => {
  req.logger.info('Creating user', { email: req.body.email });

  try {
    const user = await createUser(req.body);
    req.logger.info('User created', { user_id: user.id });
    res.json(user);
  } catch (error) {
    req.logger.error('Failed to create user', {
      error: error.message,
      stack: error.stack
    });
    res.status(500).json({ error: 'Internal error' });
  }
});
```

### Logging Best Practices

**Do:**
- Use structured JSON format
- Include correlation/trace IDs
- Log at appropriate levels
- Include relevant context
- Log timing information

**Don't:**
- Log sensitive data (passwords, tokens, PII)
- Use console.log in production
- Log at wrong levels (errors as info)
- Create high-cardinality log messages
- Log inside tight loops

### Sensitive Data Handling

```javascript
// Redaction utility
function redactSensitive(obj) {
  const sensitiveFields = ['password', 'token', 'apiKey', 'ssn', 'creditCard'];
  const redacted = { ...obj };

  for (const field of sensitiveFields) {
    if (redacted[field]) {
      redacted[field] = '[REDACTED]';
    }
  }

  return redacted;
}

// Safe logging
logger.info('Request received', redactSensitive(req.body));
```

---

## Metrics

### Metric Types

| Type | Use Case | Example |
|------|----------|---------|
| **Counter** | Cumulative, monotonic | Total requests, errors |
| **Gauge** | Point-in-time value | Current connections, queue size |
| **Histogram** | Distribution | Request latency, response size |
| **Summary** | Similar to histogram | Request duration (pre-aggregated) |

### RED Metrics (Request-driven)

```javascript
const prometheus = require('prom-client');

// Rate: Request counter
const httpRequestsTotal = new prometheus.Counter({
  name: 'http_requests_total',
  help: 'Total HTTP requests',
  labelNames: ['method', 'path', 'status']
});

// Errors: Error counter (subset of requests)
const httpErrorsTotal = new prometheus.Counter({
  name: 'http_errors_total',
  help: 'Total HTTP errors',
  labelNames: ['method', 'path', 'status', 'error_type']
});

// Duration: Request latency histogram
const httpRequestDuration = new prometheus.Histogram({
  name: 'http_request_duration_seconds',
  help: 'HTTP request duration in seconds',
  labelNames: ['method', 'path'],
  buckets: [0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10]
});

// Middleware
function metricsMiddleware(req, res, next) {
  const start = Date.now();

  res.on('finish', () => {
    const duration = (Date.now() - start) / 1000;
    const labels = {
      method: req.method,
      path: req.route?.path || req.path,
      status: res.statusCode
    };

    httpRequestsTotal.inc(labels);
    httpRequestDuration.observe(
      { method: labels.method, path: labels.path },
      duration
    );

    if (res.statusCode >= 400) {
      httpErrorsTotal.inc({
        ...labels,
        error_type: res.statusCode >= 500 ? 'server' : 'client'
      });
    }
  });

  next();
}
```

### USE Metrics (Resource-driven)

```javascript
// Utilization
const cpuUsage = new prometheus.Gauge({
  name: 'process_cpu_usage',
  help: 'Process CPU usage'
});

const memoryUsage = new prometheus.Gauge({
  name: 'process_memory_bytes',
  help: 'Process memory usage in bytes',
  labelNames: ['type']
});

// Saturation
const eventLoopLag = new prometheus.Gauge({
  name: 'nodejs_eventloop_lag_seconds',
  help: 'Node.js event loop lag in seconds'
});

const connectionPoolWaiting = new prometheus.Gauge({
  name: 'db_pool_waiting_count',
  help: 'Database connection pool waiting count'
});

// Errors
const connectionPoolErrors = new prometheus.Counter({
  name: 'db_pool_errors_total',
  help: 'Database connection pool errors',
  labelNames: ['error_type']
});

// Collection
setInterval(() => {
  const usage = process.cpuUsage();
  cpuUsage.set((usage.user + usage.system) / 1000000);

  const memory = process.memoryUsage();
  memoryUsage.set({ type: 'heap' }, memory.heapUsed);
  memoryUsage.set({ type: 'rss' }, memory.rss);
}, 5000);
```

### Label Best Practices

**Good labels:**
- method, path, status (bounded)
- service, environment (bounded)
- error_type (bounded enum)

**Bad labels (high cardinality):**
- user_id (unbounded)
- request_id (unbounded)
- timestamp (unbounded)

---

## Distributed Tracing

### Concepts

- **Trace**: End-to-end journey of a request
- **Span**: Single unit of work within a trace
- **Context**: Trace ID + Span ID propagated across services

### OpenTelemetry Setup

```javascript
const { NodeSDK } = require('@opentelemetry/sdk-node');
const { getNodeAutoInstrumentations } = require('@opentelemetry/auto-instrumentations-node');
const { OTLPTraceExporter } = require('@opentelemetry/exporter-trace-otlp-http');

const sdk = new NodeSDK({
  serviceName: process.env.SERVICE_NAME,
  traceExporter: new OTLPTraceExporter({
    url: process.env.OTEL_EXPORTER_OTLP_ENDPOINT
  }),
  instrumentations: [getNodeAutoInstrumentations()]
});

sdk.start();
```

### Manual Instrumentation

```javascript
const { trace, SpanStatusCode } = require('@opentelemetry/api');

const tracer = trace.getTracer('my-service');

async function processOrder(order) {
  return tracer.startActiveSpan('processOrder', async (span) => {
    try {
      span.setAttribute('order.id', order.id);
      span.setAttribute('order.amount', order.amount);

      // Child span for payment
      const payment = await tracer.startActiveSpan('processPayment', async (paymentSpan) => {
        try {
          const result = await paymentService.process(order);
          paymentSpan.setAttribute('payment.id', result.id);
          return result;
        } finally {
          paymentSpan.end();
        }
      });

      // Child span for inventory
      await tracer.startActiveSpan('reserveInventory', async (inventorySpan) => {
        try {
          await inventoryService.reserve(order.items);
        } finally {
          inventorySpan.end();
        }
      });

      span.setStatus({ code: SpanStatusCode.OK });
      return { success: true, paymentId: payment.id };

    } catch (error) {
      span.setStatus({
        code: SpanStatusCode.ERROR,
        message: error.message
      });
      span.recordException(error);
      throw error;
    } finally {
      span.end();
    }
  });
}
```

### Context Propagation

```javascript
// Extract context from incoming request
const { propagation, context } = require('@opentelemetry/api');

function extractContext(req) {
  return propagation.extract(context.active(), req.headers);
}

// Inject context into outgoing request
function injectContext(headers) {
  propagation.inject(context.active(), headers);
  return headers;
}

// Usage in HTTP client
async function callService(url, data) {
  const headers = injectContext({
    'Content-Type': 'application/json'
  });

  return axios.post(url, data, { headers });
}
```

### Span Attributes Best Practices

**Standard attributes:**
```javascript
span.setAttribute('http.method', 'POST');
span.setAttribute('http.url', '/api/orders');
span.setAttribute('http.status_code', 200);
span.setAttribute('db.system', 'postgresql');
span.setAttribute('db.statement', 'SELECT * FROM users');
span.setAttribute('messaging.system', 'kafka');
span.setAttribute('messaging.destination', 'orders');
```

**Custom business attributes:**
```javascript
span.setAttribute('order.id', orderId);
span.setAttribute('order.amount', amount);
span.setAttribute('user.tier', 'premium');
span.setAttribute('feature.flag', 'new-checkout');
```

---

## Correlation

### Correlation ID Flow

```
User Request
    │
    ├─ correlation_id: "abc123" (generated at edge)
    │
    ▼
API Gateway
    │
    ├─ Header: X-Correlation-ID: abc123
    │
    ▼
Service A
    │
    ├─ Log: {"correlation_id": "abc123", ...}
    ├─ Metric: request_total{correlation_id="abc123"}
    │
    ▼
Service B (via HTTP/gRPC)
    │
    ├─ Header: X-Correlation-ID: abc123
    ├─ Log: {"correlation_id": "abc123", ...}
    │
    ▼
Service C (via Queue)
    │
    ├─ Message metadata: correlation_id: abc123
    ├─ Log: {"correlation_id": "abc123", ...}
```

### Implementation

```javascript
// Middleware to handle correlation
function correlationMiddleware(req, res, next) {
  // Get from header or generate
  const correlationId = req.headers['x-correlation-id']
    || req.headers['x-request-id']
    || uuid();

  // Store in request
  req.correlationId = correlationId;

  // Add to response header
  res.setHeader('X-Correlation-ID', correlationId);

  // Add to async local storage for access anywhere
  asyncLocalStorage.run({ correlationId }, next);
}

// Get correlation ID anywhere
function getCorrelationId() {
  const store = asyncLocalStorage.getStore();
  return store?.correlationId;
}

// Logger automatically includes correlation ID
const logger = {
  info: (message, meta) => {
    console.log(JSON.stringify({
      timestamp: new Date().toISOString(),
      level: 'INFO',
      correlation_id: getCorrelationId(),
      message,
      ...meta
    }));
  }
};
```

---

## Dashboards

### Service Dashboard Template

```
┌─────────────────────────────────────────────────────────────┐
│ Service: user-service                        [Environment ▼]│
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │ Request Rate    │  │ Error Rate      │  │ Latency p99 │ │
│  │ 1,234 req/s     │  │ 0.05%           │  │ 125ms       │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Request Rate (Time Series)                              ││
│  │ ▃▄▅▆▇█▇▆▅▄▃▄▅▆▇█▇▆▅▄▃▄▅▆▇█▇▆▅▄                         ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Latency Distribution                                    ││
│  │ p50: 45ms | p95: 89ms | p99: 125ms | p999: 450ms       ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Error Rate by Type                                      ││
│  │ 5xx: 0.02% | 4xx: 0.03% | Timeout: 0.001%              ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  ┌──────────────────────┐  ┌──────────────────────────────┐│
│  │ CPU Usage            │  │ Memory Usage                 ││
│  │ 45% (limit: 2 cores) │  │ 1.2GB (limit: 4GB)          ││
│  └──────────────────────┘  └──────────────────────────────┘│
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Dependencies Health                                     ││
│  │ ✅ postgres  ✅ redis  ⚠️ payment-service (slow)       ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### Key Queries (Prometheus)

```promql
# Request rate
rate(http_requests_total{service="user-service"}[5m])

# Error rate
sum(rate(http_requests_total{service="user-service",status=~"5.."}[5m]))
/
sum(rate(http_requests_total{service="user-service"}[5m]))

# Latency percentiles
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket{service="user-service"}[5m]))

# Saturation
sum(rate(http_requests_total{service="user-service"}[5m]))
/
sum(kube_deployment_spec_replicas{deployment="user-service"} * 100)  # 100 req/s per replica capacity
```
