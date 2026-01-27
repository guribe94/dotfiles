# /fix-coupling-debt

Fix high coupling, low cohesion, instability issues, and circular dependencies.

## Usage

```
/fix-coupling-debt [path] [options]
```

### Options

- `--check <type>` - Focus on specific issue (circular, afferent, efferent, cohesion)
- `--threshold <n>` - Custom coupling threshold (default: Ce > 10 or Ca > 20)
- `--dry-run` - Show analysis without making changes

## Instructions

When the user runs `/fix-coupling-debt`:

1. **Analyze coupling metrics**:
   ```bash
   python ~/.claude/skills/tech-debt-zero/scripts/core/ast_parser.py [path] --coupling
   ```

2. **Identify issues**:
   - High Efferent Coupling (Ce > 10) - Too many dependencies
   - High Afferent Coupling (Ca > 20) - Too many dependents
   - Circular dependencies
   - Low cohesion (LCOM > 0.8)
   - Stability violations

3. **Apply appropriate fixes**:

### Breaking Circular Dependencies

**Detection:**
```bash
# Node.js
npx madge --circular src/

# Python
pydeps --show-cycles mypackage
```

**Fix Strategy 1: Dependency Inversion**

```
Before: A → B → C → A (cycle)

After:
- Extract interface IB from B
- A depends on IB (not B)
- B implements IB
- Cycle broken
```

```javascript
// Before: circular dependency
// moduleA.js
const { funcB } = require('./moduleB')
exports.funcA = () => funcB()

// moduleB.js
const { funcA } = require('./moduleA')  // Circular!
exports.funcB = () => funcA()

// After: interface extraction
// interfaces.js
exports.IModuleA = class IModuleA {
  funcA() { throw new Error('Not implemented') }
}

// moduleA.js
const { IModuleA } = require('./interfaces')
class ModuleA extends IModuleA {
  constructor(moduleB) { this.moduleB = moduleB }
  funcA() { return this.moduleB.funcB() }
}

// moduleB.js (no longer imports A)
class ModuleB {
  funcB() { return 'B' }
}

// composition.js (wires everything)
const moduleB = new ModuleB()
const moduleA = new ModuleA(moduleB)
```

**Fix Strategy 2: Extract Common Module**

```
Before: A → B, B → A (shared logic)

After:
- Extract shared logic to C
- A → C, B → C
- No cycle
```

### Reducing Efferent Coupling (Ce)

**Problem:** Module depends on too many other modules (fragile).

**Fix Strategy 1: Facade Pattern**

```javascript
// Before: Service depends on 10 modules
class OrderService {
  constructor() {
    this.userService = new UserService()
    this.productService = new ProductService()
    this.inventoryService = new InventoryService()
    this.paymentService = new PaymentService()
    this.shippingService = new ShippingService()
    this.notificationService = new NotificationService()
    this.analyticsService = new AnalyticsService()
    this.taxService = new TaxService()
    this.discountService = new DiscountService()
    this.auditService = new AuditService()
  }
}

// After: Facades reduce direct dependencies
class OrderService {
  constructor(
    orderFulfillment,  // Encapsulates inventory, shipping
    orderPayment,      // Encapsulates payment, tax, discount
    orderNotification  // Encapsulates notification, analytics, audit
  ) {
    this.fulfillment = orderFulfillment
    this.payment = orderPayment
    this.notification = orderNotification
  }
}
```

**Fix Strategy 2: Dependency Injection**

```javascript
// Before: Hard dependencies
class OrderService {
  constructor() {
    this.db = new PostgresDatabase()
    this.cache = new RedisCache()
    this.queue = new RabbitMQ()
  }
}

// After: Injected abstractions
class OrderService {
  constructor(db, cache, queue) {
    this.db = db      // IDatabase
    this.cache = cache  // ICache
    this.queue = queue  // IQueue
  }
}

// Composition root wires concrete implementations
const orderService = new OrderService(
  new PostgresDatabase(),
  new RedisCache(),
  new RabbitMQ()
)
```

### Reducing Afferent Coupling (Ca)

**Problem:** Too many modules depend on this module (hard to change).

**Fix Strategy: Extract Stable Interface**

```javascript
// Before: Many modules depend on UserService directly
// Changes to UserService break many dependents

// After: Extract stable interface
// user.interface.ts
export interface IUserService {
  getUser(id: string): Promise<User>
  createUser(data: UserData): Promise<User>
}

// user.service.ts
export class UserService implements IUserService {
  // Implementation can change without breaking dependents
}

// Dependents import interface, not implementation
import { IUserService } from './user.interface'
```

### Improving Cohesion (LCOM)

**Problem:** Class methods don't share state (should be split).

**Detection:**
```javascript
// Low cohesion: methods in two groups that don't share fields
class UserManager {
  // Group 1: User CRUD
  private userDb: Database

  createUser() { this.userDb.insert() }
  findUser() { return this.userDb.find() }

  // Group 2: Email (doesn't use userDb)
  private emailClient: EmailClient

  sendWelcomeEmail() { this.emailClient.send() }
  sendPasswordReset() { this.emailClient.send() }
}
// LCOM = 2 (two connected components)
```

**Fix: Split into cohesive classes**
```javascript
// High cohesion: each class uses all its fields
class UserRepository {
  private db: Database

  create() { this.db.insert() }
  find() { return this.db.find() }
  update() { this.db.update() }
  delete() { this.db.delete() }
}

class UserEmailService {
  private emailClient: EmailClient
  private userRepo: UserRepository

  sendWelcome(userId) {
    const user = this.userRepo.find(userId)
    this.emailClient.send(user.email, 'Welcome!')
  }

  sendPasswordReset(userId) {
    const user = this.userRepo.find(userId)
    this.emailClient.send(user.email, 'Reset...')
  }
}
```

### Fixing Stability Violations

**Rule:** Dependencies should flow from unstable to stable.

```
Instability I = Ce / (Ca + Ce)
I = 0: Maximally stable (many dependents, no dependencies)
I = 1: Maximally unstable (no dependents, many dependencies)
```

**Violation:** Stable module depends on unstable module.

```javascript
// VIOLATION: Core domain (stable) depends on Controller (unstable)
// core/order.ts (I ≈ 0, stable)
import { OrderController } from '../controllers/order'  // Wrong!

// FIX: Invert the dependency
// controllers/order.ts (I ≈ 1, unstable)
import { Order } from '../core/order'  // Correct direction
```

4. **Verify the fix**:
   - Re-run coupling analysis
   - Run tests to verify behavior unchanged
   - Check circular dependencies resolved

## Metrics Reference

| Metric | Good | Warning | Critical |
|--------|------|---------|----------|
| Ce (efferent) | < 5 | 5-10 | > 10 |
| Ca (afferent) | < 10 | 10-20 | > 20 |
| LCOM | 1 | 2 | > 2 |
| Circular deps | 0 | 1-2 | > 2 |

## Refactoring Sequence

1. Add tests to affected modules
2. Break circular dependencies first
3. Extract interfaces for high-Ca modules
4. Use facades for high-Ce modules
5. Split low-cohesion classes
6. Verify metrics improved
7. Run full test suite

## Tools

```bash
# Node.js - circular dependency detection
npx madge --circular src/

# Node.js - dependency graph
npx madge --image graph.svg src/

# Python - dependency analysis
pydeps mypackage --max-bacon=2
```

## References

- Robert C. Martin - Clean Architecture
- Agile Software Development, Principles, Patterns, and Practices
- Coupling metrics: Ca, Ce, Instability (Robert Martin)
- LCOM (Chidamber and Kemerer)
