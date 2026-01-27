# Coupling Metrics

Measuring and improving coupling and cohesion in codebases.

---

## Key Metrics

### Afferent Coupling (Ca)

**Definition:** Number of classes/modules that depend ON this module.

```
Module A
   ↓
   ├── Used by Module B
   ├── Used by Module C
   └── Used by Module D

Ca(A) = 3
```

**Interpretation:**
- High Ca = Many dependents = Hard to change (changes ripple outward)
- High Ca modules should be stable (interfaces, core abstractions)

| Ca | Assessment |
|----|------------|
| 0-5 | Low - easy to change |
| 6-15 | Medium - change carefully |
| 16+ | High - very stable, change requires coordination |

### Efferent Coupling (Ce)

**Definition:** Number of classes/modules that this module depends ON.

```
Module A
   ↓
   ├── Depends on Module X
   ├── Depends on Module Y
   └── Depends on Module Z

Ce(A) = 3
```

**Interpretation:**
- High Ce = Many dependencies = Fragile (changes from dependencies affect it)
- High Ce modules should be concrete, close to I/O

| Ce | Assessment |
|----|------------|
| 0-5 | Low - isolated, stable |
| 6-10 | Medium - some coupling |
| 11+ | High - fragile, consider splitting |

### Instability Index (I)

**Definition:** `I = Ce / (Ca + Ce)`

**Interpretation:**
- I = 0: Maximally stable (all incoming dependencies, no outgoing)
- I = 1: Maximally unstable (all outgoing dependencies, no incoming)

**Architecture Rule:** Dependencies should flow from unstable to stable.

```
Unstable (I=1)     →     Stable (I=0)
Controllers        →     Services         →     Domain
UI Components      →     Business Logic   →     Core Abstractions
```

**Violation Detection:**
```python
def check_stability_violation(module_a, module_b, dependency):
    """
    module_a depends on module_b
    Violation if: I(module_a) < I(module_b)
    (stable depending on unstable)
    """
    if module_a.instability < module_b.instability:
        return f"Stability violation: {module_a.name} (I={module_a.instability}) depends on {module_b.name} (I={module_b.instability})"
    return None
```

### Abstractness (A)

**Definition:** `A = Abstract classes / Total classes`

**Interpretation:**
- A = 0: All concrete classes
- A = 1: All abstract classes/interfaces

### Distance from Main Sequence (D)

**Definition:** `D = |A + I - 1|`

**Interpretation:**
- D = 0: Ideal balance of stability and abstractness
- D > 0.5: In "zone of pain" or "zone of uselessness"

```
       1 ┌─────────────────────┐
         │    Zone of         │
    A    │    Uselessness     │
         │  (abstract but     │
         │   unstable)        │
         │         Main       │
       0.5├─────── Sequence ──┤
         │                    │
         │    Zone of Pain    │
         │  (concrete but     │
         │   stable)          │
       0 └─────────────────────┘
         0        0.5          1
                  I (Instability)
```

---

## Cohesion Metrics

### LCOM (Lack of Cohesion of Methods)

**LCOM1:** Count of method pairs that share no instance variables minus count of method pairs that do share instance variables.

**LCOM4 (Preferred):** Number of connected components in the class's method-attribute graph.

```python
def calculate_lcom4(cls):
    """
    Build graph where:
    - Nodes are methods
    - Edges connect methods that share instance variables

    LCOM4 = number of connected components
    LCOM4 = 1: Cohesive (all methods connected)
    LCOM4 > 1: Consider splitting into LCOM4 classes
    """
    graph = build_method_graph(cls)
    return count_connected_components(graph)
```

**Example:**
```javascript
class LowCohesion {
  // Group 1: User methods
  createUser() { this.userDb.insert(); }
  findUser() { return this.userDb.find(); }

  // Group 2: Order methods (no shared state with Group 1)
  createOrder() { this.orderDb.insert(); }
  findOrder() { return this.orderDb.find(); }
}
// LCOM4 = 2 → Should split into UserRepository and OrderRepository
```

| LCOM4 | Assessment |
|-------|------------|
| 1 | Cohesive - good |
| 2 | Consider splitting |
| 3+ | Definitely split |

---

## Circular Dependencies

### Detection

```python
def find_cycles(modules):
    """
    DFS-based cycle detection in module dependency graph.
    """
    visited = set()
    path = []
    cycles = []

    def dfs(module):
        if module in path:
            cycle_start = path.index(module)
            cycles.append(path[cycle_start:] + [module])
            return
        if module in visited:
            return

        visited.add(module)
        path.append(module)

        for dep in module.dependencies:
            dfs(dep)

        path.pop()

    for module in modules:
        dfs(module)

    return cycles
```

### Breaking Cycles

**Strategy 1: Dependency Inversion**
```
Before: A → B → C → A (cycle)

After:
A → IB (interface)
B implements IB
B → IC (interface)
C implements IC
C → IA (interface)
A implements IA
```

**Strategy 2: Extract Common Dependency**
```
Before: A → B → A (both need shared logic)

After:
Common module extracted
A → Common
B → Common
No cycle!
```

**Strategy 3: Merge Modules**
```
Before: A ↔ B (tightly coupled)

After:
AB (merged module)
If they're that coupled, maybe they're one concept
```

---

## Measurement Tools

### JavaScript/TypeScript

```bash
# Madge - circular dependency detection
npx madge --circular src/

# Madge - dependency graph
npx madge --image graph.svg src/

# dependency-cruiser - comprehensive
npx depcruise --include-only "^src" --output-type dot src | dot -T svg > deps.svg
```

### Python

```bash
# pydeps - dependency graph
pydeps mypackage --max-bacon=2

# import-linter - architecture enforcement
import-linter
```

### Configuration Example (dependency-cruiser)

```javascript
// .dependency-cruiser.js
module.exports = {
  forbidden: [
    {
      name: 'no-circular',
      severity: 'error',
      from: {},
      to: { circular: true }
    },
    {
      name: 'no-orphans',
      severity: 'warn',
      from: { orphan: true },
      to: {}
    },
    {
      name: 'domain-no-infra',
      comment: 'Domain should not depend on infrastructure',
      severity: 'error',
      from: { path: '^src/domain' },
      to: { path: '^src/infrastructure' }
    },
    {
      name: 'stable-dependencies',
      comment: 'Unstable modules should not be depended on by stable modules',
      severity: 'error',
      from: { path: '^src/core' },
      to: { path: '^src/(controllers|api)' }
    }
  ],
  options: {
    doNotFollow: { path: 'node_modules' }
  }
};
```

---

## Architecture Layers

### Clean Architecture Dependency Rules

```
┌─────────────────────────────────────┐
│          Frameworks & Drivers       │  Ce: High, Ca: Low, I: ~1
│         (Express, Postgres)         │
├─────────────────────────────────────┤
│         Interface Adapters          │  Balanced
│      (Controllers, Repositories)    │
├─────────────────────────────────────┤
│          Application Layer          │  Balanced
│           (Use Cases)               │
├─────────────────────────────────────┤
│           Domain Layer              │  Ca: High, Ce: Low, I: ~0
│     (Entities, Value Objects)       │
└─────────────────────────────────────┘

Dependencies point INWARD only
```

### Enforcement

```python
LAYER_RULES = {
    'domain': {
        'can_depend_on': [],  # Nothing
        'cannot_depend_on': ['application', 'adapters', 'infrastructure']
    },
    'application': {
        'can_depend_on': ['domain'],
        'cannot_depend_on': ['adapters', 'infrastructure']
    },
    'adapters': {
        'can_depend_on': ['domain', 'application'],
        'cannot_depend_on': ['infrastructure']
    },
    'infrastructure': {
        'can_depend_on': ['domain', 'application', 'adapters'],
        'cannot_depend_on': []
    }
}

def check_layer_violation(from_module, to_module):
    from_layer = get_layer(from_module)
    to_layer = get_layer(to_module)

    if to_layer in LAYER_RULES[from_layer]['cannot_depend_on']:
        return f"Layer violation: {from_layer} cannot depend on {to_layer}"
    return None
```

---

## Coupling Score

### Composite Metric

```python
def calculate_coupling_score(module):
    """
    Combined coupling health score (0-100, higher is better).
    """
    # Normalize metrics
    ca_score = max(0, 100 - module.ca * 5)  # Penalize high Ca
    ce_score = max(0, 100 - module.ce * 8)  # Penalize high Ce more
    lcom_score = max(0, 100 - (module.lcom4 - 1) * 30)  # Penalize LCOM > 1
    cycles_score = 100 if not module.in_cycle else 0

    # Check stability direction
    stability_score = 100
    for dep in module.dependencies:
        if module.instability < dep.instability:
            stability_score -= 20

    # Weighted average
    return (
        ca_score * 0.15 +
        ce_score * 0.25 +
        lcom_score * 0.20 +
        cycles_score * 0.25 +
        stability_score * 0.15
    )
```

### Thresholds

| Score | Assessment | Action |
|-------|------------|--------|
| 80-100 | Healthy | Maintain |
| 60-79 | Warning | Plan improvement |
| 40-59 | Poor | Prioritize refactoring |
| 0-39 | Critical | Immediate action |

---

## Improvement Strategies

### Reducing Efferent Coupling (Ce)

1. **Facade Pattern** - Hide complex subsystem behind simple interface
2. **Dependency Injection** - Decouple from concrete implementations
3. **Event-Driven** - Replace direct calls with events
4. **Split Module** - Extract independent responsibilities

### Reducing Afferent Coupling (Ca)

1. **Versioning** - Allow old and new interfaces
2. **Interface Extraction** - Depend on interface, not implementation
3. **Deprecation** - Gradually migrate dependents

### Improving Cohesion (LCOM)

1. **Extract Class** - Split unrelated method groups
2. **Move Method** - Relocate methods to proper class
3. **Rename** - Clarify class purpose, remove unrelated methods
