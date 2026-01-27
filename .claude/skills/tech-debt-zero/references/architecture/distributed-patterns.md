# Distributed Systems Patterns

Patterns for distributed system debt and anti-patterns.

---

## Distributed Monolith

### Detection

**Symptoms:**
- Deploy all services together
- Shared database between services
- Synchronous chains across many services
- One service failure cascades to all
- Can't release services independently

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│Service A│───▶│Service B│───▶│Service C│───▶│Service D│
└─────────┘    └─────────┘    └─────────┘    └─────────┘
     │              │              │              │
     └──────────────┴──────────────┴──────────────┘
                         │
                   ┌─────────┐
                   │ Shared  │
                   │   DB    │
                   └─────────┘
```

### Metrics

```python
def detect_distributed_monolith(services):
    issues = []

    # Check for shared databases
    db_to_services = {}
    for service in services:
        for db in service.databases:
            db_to_services.setdefault(db, []).append(service)

    for db, svcs in db_to_services.items():
        if len(svcs) > 1:
            issues.append(f"Shared database {db}: {[s.name for s in svcs]}")

    # Check for synchronous chains
    for service in services:
        chain_length = calculate_sync_chain_length(service)
        if chain_length > 3:
            issues.append(f"Long sync chain from {service.name}: {chain_length} hops")

    # Check deployment coupling
    deploy_groups = find_co_deployed_services(services)
    for group in deploy_groups:
        if len(group) > 2:
            issues.append(f"Co-deployed services: {group}")

    return issues
```

### Fix Patterns

**Database per Service:**
```
Before: Services A, B, C → Shared DB

After:
Service A → DB-A (owns users table)
Service B → DB-B (owns orders table)
Service C → DB-C (owns products table)

Cross-service data via:
- API calls
- Events
- Materialized views (read replicas)
```

**Async Communication:**
```
Before: A → B → C (sync chain)

After:
A publishes OrderCreated event
B subscribes, processes, publishes OrderProcessed
C subscribes, processes independently

Benefits:
- Services decoupled
- Can scale independently
- Failures isolated
```

---

## Chatty Services

### Detection

**Symptoms:**
- N+1 queries across service boundaries
- Multiple round trips for single operation
- High latency due to network calls
- Amplified failure rates

```javascript
// Anti-pattern: N+1 across services
async function getOrdersWithProducts(userId) {
  const orders = await orderService.getByUser(userId);  // 1 call

  // N additional calls!
  for (const order of orders) {
    order.products = await productService.getByIds(order.productIds);
  }

  return orders;
}
```

### Metrics

```python
def detect_chatty_services(service_calls):
    """
    Detect N+1 patterns in service calls.
    """
    issues = []

    # Group calls by trace
    for trace_id, calls in group_by_trace(service_calls).items():
        # Count calls per service
        service_counts = Counter(c.target_service for c in calls)

        for service, count in service_counts.items():
            if count > 5:  # Threshold for N+1
                issues.append({
                    'trace_id': trace_id,
                    'target_service': service,
                    'call_count': count,
                    'pattern': 'N+1'
                })

    return issues
```

### Fix Patterns

**Batch APIs:**
```javascript
// Fixed: Batch call
async function getOrdersWithProducts(userId) {
  const orders = await orderService.getByUser(userId);

  // Single batch call
  const allProductIds = orders.flatMap(o => o.productIds);
  const products = await productService.getByIds(allProductIds);  // 1 call

  // Map products to orders
  const productMap = new Map(products.map(p => [p.id, p]));
  for (const order of orders) {
    order.products = order.productIds.map(id => productMap.get(id));
  }

  return orders;
}
```

**GraphQL/BFF (Backend for Frontend):**
```javascript
// BFF aggregates data in single call to client
const bff = {
  async getOrdersPage(userId) {
    const [orders, products, user] = await Promise.all([
      orderService.getByUser(userId),
      productService.getPopular(),
      userService.get(userId)
    ]);

    return { orders, products, user };  // Single response to client
  }
};
```

---

## Data Consistency

### Patterns

**Saga Pattern:**
```javascript
// Orchestrated saga for distributed transaction
class OrderSaga {
  async execute(orderData) {
    const compensations = [];

    try {
      // Step 1: Reserve inventory
      const reservation = await inventoryService.reserve(orderData.items);
      compensations.push(() => inventoryService.release(reservation.id));

      // Step 2: Process payment
      const payment = await paymentService.charge(orderData.payment);
      compensations.push(() => paymentService.refund(payment.id));

      // Step 3: Create order
      const order = await orderService.create(orderData);

      return { success: true, orderId: order.id };

    } catch (error) {
      // Execute compensations in reverse order
      for (const compensate of compensations.reverse()) {
        try {
          await compensate();
        } catch (compError) {
          // Log and continue - compensations must be idempotent
          logger.error('Compensation failed', compError);
        }
      }

      return { success: false, error: error.message };
    }
  }
}
```

**Outbox Pattern:**
```javascript
// Ensure event is published atomically with database change
async function createOrder(orderData) {
  const connection = await db.getConnection();

  try {
    await connection.beginTransaction();

    // Insert order
    const order = await connection.query(
      'INSERT INTO orders (...) VALUES (...)',
      orderData
    );

    // Insert event into outbox (same transaction!)
    await connection.query(
      'INSERT INTO outbox (event_type, payload) VALUES (?, ?)',
      ['OrderCreated', JSON.stringify(order)]
    );

    await connection.commit();

    // Background process polls outbox and publishes events
    return order;

  } catch (error) {
    await connection.rollback();
    throw error;
  }
}
```

### Detection

```python
def detect_consistency_issues(codebase):
    issues = []

    # Check for distributed transactions without saga
    for func in codebase.functions:
        services_called = extract_service_calls(func)
        if len(services_called) > 1:
            if not has_compensation_logic(func):
                issues.append({
                    'function': func.name,
                    'services': services_called,
                    'issue': 'Multi-service call without saga pattern'
                })

    # Check for event publish without outbox
    for func in codebase.functions:
        if has_db_write(func) and has_event_publish(func):
            if not uses_outbox_pattern(func):
                issues.append({
                    'function': func.name,
                    'issue': 'Event publish not atomic with DB write'
                })

    return issues
```

---

## Event Sourcing Debt

### Common Issues

**1. Missing Event Versioning:**
```javascript
// Bad: No version
{ type: 'OrderCreated', orderId: '123', items: [...] }

// Good: Versioned schema
{
  type: 'OrderCreated',
  version: 2,
  orderId: '123',
  items: [...],
  metadata: { timestamp: '...', correlationId: '...' }
}
```

**2. Breaking Schema Changes:**
```javascript
// Upcaster for backward compatibility
class OrderCreatedUpcaster {
  canUpcast(event) {
    return event.type === 'OrderCreated' && event.version < 2;
  }

  upcast(event) {
    if (event.version === 1) {
      return {
        ...event,
        version: 2,
        items: event.products.map(p => ({ productId: p.id, quantity: p.qty })),
        metadata: { timestamp: event.timestamp }
      };
    }
    return event;
  }
}
```

**3. DLQ Handling:**
```javascript
class DeadLetterHandler {
  async processDeadLetter(message) {
    const { event, error, attempts } = message;

    // Log for investigation
    logger.error('Dead letter', { event, error, attempts });

    // Determine action
    if (isRetryable(error) && attempts < 5) {
      await this.requeueWithBackoff(message);
    } else {
      // Store for manual intervention
      await this.storeForManualReview(message);
      await this.alertOps(message);
    }
  }
}
```

### Detection

```python
def detect_event_debt(codebase):
    issues = []

    # Check for unversioned events
    for event_class in codebase.event_classes:
        if not has_version_field(event_class):
            issues.append(f"Unversioned event: {event_class.name}")

    # Check for missing upcasters
    event_versions = collect_event_versions(codebase)
    for event_type, versions in event_versions.items():
        if len(versions) > 1:
            for old_version in versions[:-1]:
                if not has_upcaster(event_type, old_version):
                    issues.append(f"Missing upcaster: {event_type} v{old_version}")

    # Check DLQ handling
    for queue in codebase.queues:
        if queue.has_dlq and not queue.has_dlq_handler:
            issues.append(f"Unhandled DLQ: {queue.name}")

    return issues
```

---

## Service Mesh Debt

### Common Issues

**1. Missing Timeouts:**
```yaml
# Istio VirtualService without timeout
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
spec:
  http:
    - route:
        - destination:
            host: my-service
      # Missing: timeout

# Fixed
spec:
  http:
    - route:
        - destination:
            host: my-service
      timeout: 10s
      retries:
        attempts: 3
        perTryTimeout: 3s
```

**2. Missing Circuit Breakers:**
```yaml
# DestinationRule without outlier detection
apiVersion: networking.istio.io/v1alpha3
kind: DestinationRule
spec:
  host: my-service
  trafficPolicy:
    # Missing: outlierDetection

# Fixed
spec:
  host: my-service
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```

---

## API Gateway Debt

### Common Issues

**1. Missing Rate Limiting:**
```yaml
# Kong rate limiting
plugins:
  - name: rate-limiting
    config:
      minute: 100
      hour: 1000
      policy: local
```

**2. Missing Auth:**
```yaml
# Ensure auth on all routes
routes:
  - path: /api/public/*
    plugins: []  # No auth - explicitly public

  - path: /api/*
    plugins:
      - name: jwt
        config:
          secret: ${JWT_SECRET}
```

---

## Checklist

### Service Independence

- [ ] Each service owns its data
- [ ] Can deploy services independently
- [ ] Service failure is isolated
- [ ] No shared libraries with business logic

### Communication

- [ ] Async where possible
- [ ] Batch APIs for bulk operations
- [ ] Timeouts on all external calls
- [ ] Circuit breakers on failure-prone calls
- [ ] Idempotent operations

### Data Consistency

- [ ] Saga pattern for distributed transactions
- [ ] Outbox pattern for event publishing
- [ ] Compensating transactions defined
- [ ] Eventual consistency acceptable where used

### Events

- [ ] Events are versioned
- [ ] Upcasters for old versions
- [ ] DLQ handling defined
- [ ] Event schema registry
