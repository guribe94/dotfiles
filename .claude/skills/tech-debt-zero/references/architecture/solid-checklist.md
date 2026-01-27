# SOLID Principles Checklist

Detecting and fixing SOLID principle violations.

---

## Single Responsibility Principle (SRP)

> A class should have only one reason to change.

### Detection

**Symptoms:**
- Class has >20 methods
- Class has >500 lines
- Class name includes "Manager", "Handler", "Processor", "Service" with many unrelated methods
- Multiple distinct groups of methods
- Too many dependencies injected

```javascript
// VIOLATION: Multiple responsibilities
class UserManager {
  // User CRUD - responsibility 1
  createUser(data) { ... }
  updateUser(id, data) { ... }
  deleteUser(id) { ... }

  // Email - responsibility 2
  sendWelcomeEmail(user) { ... }
  sendPasswordReset(user) { ... }

  // Reporting - responsibility 3
  generateUserReport() { ... }
  exportToCSV() { ... }

  // Analytics - responsibility 4
  trackUserActivity(user, action) { ... }
  calculateEngagementScore(user) { ... }
}
```

### Fix

```javascript
// FIXED: Separate classes per responsibility
class UserRepository {
  create(data) { ... }
  update(id, data) { ... }
  delete(id) { ... }
  findById(id) { ... }
}

class UserEmailService {
  constructor(emailClient, userRepository) { ... }
  sendWelcome(userId) { ... }
  sendPasswordReset(userId) { ... }
}

class UserReportGenerator {
  constructor(userRepository) { ... }
  generate() { ... }
  exportToCSV() { ... }
}

class UserAnalytics {
  constructor(analyticsClient) { ... }
  trackActivity(userId, action) { ... }
  calculateEngagement(userId) { ... }
}
```

### Checklist

- [ ] Each class has a single, well-defined purpose
- [ ] Class name clearly describes its one responsibility
- [ ] Methods are cohesive (use shared state)
- [ ] Changes to one aspect don't require changing others
- [ ] Class has ~3-7 dependencies max

---

## Open/Closed Principle (OCP)

> Software entities should be open for extension, closed for modification.

### Detection

**Symptoms:**
- Excessive `if/else` or `switch` on type
- `instanceof` checks throughout code
- Adding new features requires modifying existing code
- Feature flags embedded in core logic

```javascript
// VIOLATION: Must modify to add new payment type
class PaymentProcessor {
  process(payment) {
    if (payment.type === 'credit') {
      return this.processCreditCard(payment);
    } else if (payment.type === 'paypal') {
      return this.processPayPal(payment);
    } else if (payment.type === 'crypto') {  // Had to modify!
      return this.processCrypto(payment);
    }
    throw new Error('Unknown payment type');
  }
}
```

### Fix

```javascript
// FIXED: Strategy pattern - extend without modifying
interface PaymentStrategy {
  canHandle(payment: Payment): boolean;
  process(payment: Payment): Promise<PaymentResult>;
}

class CreditCardStrategy implements PaymentStrategy {
  canHandle(payment) { return payment.type === 'credit'; }
  process(payment) { ... }
}

class PayPalStrategy implements PaymentStrategy {
  canHandle(payment) { return payment.type === 'paypal'; }
  process(payment) { ... }
}

// Adding crypto is just adding a new class - no modification needed
class CryptoStrategy implements PaymentStrategy {
  canHandle(payment) { return payment.type === 'crypto'; }
  process(payment) { ... }
}

class PaymentProcessor {
  constructor(strategies: PaymentStrategy[]) {
    this.strategies = strategies;
  }

  process(payment) {
    const strategy = this.strategies.find(s => s.canHandle(payment));
    if (!strategy) throw new Error('No handler for payment type');
    return strategy.process(payment);
  }
}
```

### Checklist

- [ ] No switch/if-else on type that grows over time
- [ ] New features added via new code, not modification
- [ ] Uses patterns: Strategy, Template Method, Decorator
- [ ] Interfaces define extension points
- [ ] Core logic stable, extensions vary

---

## Liskov Substitution Principle (LSP)

> Objects of a superclass should be replaceable with objects of subclasses without affecting program correctness.

### Detection

**Symptoms:**
- Subclass throws exceptions parent doesn't
- Subclass ignores parent method behavior
- `instanceof` checks in code using base type
- Empty method implementations
- Preconditions strengthened in subclass
- Postconditions weakened in subclass

```javascript
// VIOLATION: Square is not substitutable for Rectangle
class Rectangle {
  setWidth(w) { this.width = w; }
  setHeight(h) { this.height = h; }
  area() { return this.width * this.height; }
}

class Square extends Rectangle {
  setWidth(w) {
    this.width = w;
    this.height = w;  // Breaks expectation!
  }
  setHeight(h) {
    this.width = h;   // Breaks expectation!
    this.height = h;
  }
}

// This breaks with Square
function testRectangle(rect) {
  rect.setWidth(5);
  rect.setHeight(4);
  assert(rect.area() === 20);  // Fails for Square!
}
```

### Fix

```javascript
// FIXED: Don't use inheritance for non-substitutable types
interface Shape {
  area(): number;
}

class Rectangle implements Shape {
  constructor(public width: number, public height: number) {}
  area() { return this.width * this.height; }
}

class Square implements Shape {
  constructor(public side: number) {}
  area() { return this.side * this.side; }
}

// Or use composition
class Square {
  private rect: Rectangle;

  constructor(side: number) {
    this.rect = new Rectangle(side, side);
  }

  setSide(s: number) {
    this.rect = new Rectangle(s, s);
  }

  area() { return this.rect.area(); }
}
```

### Checklist

- [ ] Subclasses honor parent's contract
- [ ] No instanceof checks needed when using base type
- [ ] Subclasses don't throw new exception types
- [ ] Method preconditions equal or weaker
- [ ] Method postconditions equal or stronger
- [ ] Invariants maintained

---

## Interface Segregation Principle (ISP)

> Clients should not be forced to depend on interfaces they do not use.

### Detection

**Symptoms:**
- Classes implement interfaces with unused methods
- Empty or throw-only method implementations
- "Fat" interfaces with many unrelated methods
- Changes to interface affect unrelated implementers

```javascript
// VIOLATION: Fat interface
interface Worker {
  work(): void;
  eat(): void;
  sleep(): void;
  getPaid(): void;
}

class Robot implements Worker {
  work() { ... }
  eat() { throw new Error('Robots do not eat'); }   // Violation!
  sleep() { throw new Error('Robots do not sleep'); } // Violation!
  getPaid() { throw new Error('Robots do not get paid'); } // Violation!
}
```

### Fix

```javascript
// FIXED: Segregated interfaces
interface Workable {
  work(): void;
}

interface Eatable {
  eat(): void;
}

interface Sleepable {
  sleep(): void;
}

interface Payable {
  getPaid(): void;
}

class Human implements Workable, Eatable, Sleepable, Payable {
  work() { ... }
  eat() { ... }
  sleep() { ... }
  getPaid() { ... }
}

class Robot implements Workable {
  work() { ... }
  // Only implements what it needs!
}
```

### Checklist

- [ ] Interfaces are small and focused
- [ ] No empty/throw implementations
- [ ] Clients only depend on methods they use
- [ ] Interface changes have minimal ripple effect
- [ ] Prefer many small interfaces to few large ones

---

## Dependency Inversion Principle (DIP)

> High-level modules should not depend on low-level modules. Both should depend on abstractions.

### Detection

**Symptoms:**
- `new` in business logic
- Direct imports of concrete implementations
- Hard to test without real dependencies
- Cannot swap implementations
- Framework/library code in domain layer

```javascript
// VIOLATION: Direct dependency on concrete implementations
class OrderService {
  constructor() {
    this.db = new PostgresDatabase();  // Concrete!
    this.emailer = new SendGridEmailer();  // Concrete!
    this.logger = new WinstonLogger();  // Concrete!
  }

  async createOrder(order) {
    await this.db.save(order);
    await this.emailer.send(order.email, 'Order created');
    this.logger.info('Order created');
  }
}

// Hard to test - needs real Postgres, SendGrid, etc.
```

### Fix

```javascript
// FIXED: Depend on abstractions
interface Database {
  save(entity: any): Promise<void>;
  findById(id: string): Promise<any>;
}

interface Emailer {
  send(to: string, message: string): Promise<void>;
}

interface Logger {
  info(message: string): void;
  error(message: string, error?: Error): void;
}

class OrderService {
  constructor(
    private db: Database,
    private emailer: Emailer,
    private logger: Logger
  ) {}

  async createOrder(order) {
    await this.db.save(order);
    await this.emailer.send(order.email, 'Order created');
    this.logger.info('Order created');
  }
}

// Easy to test with mocks
class MockDatabase implements Database {
  save = jest.fn();
  findById = jest.fn();
}

// Easy to swap implementations
const service = new OrderService(
  new PostgresDatabase(),
  new SendGridEmailer(),
  new WinstonLogger()
);

// Or for testing
const testService = new OrderService(
  new MockDatabase(),
  new MockEmailer(),
  new ConsoleLogger()
);
```

### Checklist

- [ ] No `new` for services/repositories in business logic
- [ ] Dependencies injected via constructor
- [ ] Interfaces/abstractions at module boundaries
- [ ] High-level policy doesn't know low-level details
- [ ] Easy to swap implementations
- [ ] Easy to mock for testing

---

## Detection Script Patterns

```python
# SOLID violation detection patterns

SRP_PATTERNS = {
    'too_many_methods': lambda cls: len(cls.methods) > 20,
    'too_many_lines': lambda cls: cls.line_count > 500,
    'multiple_responsibilities': lambda cls: len(cls.method_groups) > 3,
    'too_many_dependencies': lambda cls: len(cls.dependencies) > 7,
}

OCP_PATTERNS = {
    'type_switch': r'switch\s*\([^)]+\.type\)',
    'instanceof_chain': r'instanceof\s+\w+.*instanceof',
    'if_else_type': r'if\s*\([^)]+\.type\s*===',
}

LSP_PATTERNS = {
    'empty_override': r'^\s*\w+\([^)]*\)\s*{\s*}',
    'throw_in_override': r'throw new.*not (supported|implemented)',
}

ISP_PATTERNS = {
    'empty_implementation': lambda method: method.body_is_empty,
    'throw_not_implemented': lambda method: 'NotImplemented' in method.body,
}

DIP_PATTERNS = {
    'new_in_constructor': r'this\.\w+\s*=\s*new\s+\w+',
    'concrete_import': lambda imp: not imp.is_interface,
}
```

---

## Refactoring Sequence

1. **Add tests** for existing behavior
2. **Identify violation** and scope
3. **Extract interface** if needed (DIP, ISP)
4. **Split class** if needed (SRP)
5. **Introduce pattern** if needed (OCP: Strategy, Template Method)
6. **Fix inheritance** if needed (LSP: composition over inheritance)
7. **Inject dependencies** (DIP)
8. **Verify tests** still pass
9. **Remove dead code**
