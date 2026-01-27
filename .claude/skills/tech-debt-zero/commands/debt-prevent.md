# /debt-prevent

Generate quality gates for CI/CD to prevent new tech debt.

## Usage

```
/debt-prevent [output-type] [options]
```

### Output Types

- `pre-commit` - Generate pre-commit hook configuration
- `github-actions` - Generate GitHub Actions workflow
- `gitlab-ci` - Generate GitLab CI pipeline
- `all` - Generate all configurations

### Options

- `--strict` - Use strict thresholds (fail on medium+)
- `--security-only` - Only security gates
- `--output <path>` - Write to file instead of stdout

### Examples

```bash
# Generate pre-commit hooks
/debt-prevent pre-commit > .pre-commit-config.yaml

# Generate GitHub Actions workflow
/debt-prevent github-actions > .github/workflows/tech-debt.yml

# Generate all with strict mode
/debt-prevent all --strict

# Security-focused gates for CI
/debt-prevent github-actions --security-only
```

## Instructions

When the user runs `/debt-prevent`:

1. **Determine project type** by checking for:
   - package.json (Node.js)
   - requirements.txt/pyproject.toml (Python)
   - go.mod (Go)
   - Cargo.toml (Rust)

2. **Generate appropriate configuration** for the requested type

3. **Include gates for**:
   - Secret detection
   - Dependency vulnerability scanning
   - Security linting
   - Type checking (if applicable)
   - Test coverage
   - Resilience checks (timeouts)

4. **Explain the gates** and how to customize

## Generated Configurations

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  # Secret Detection
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']

  # Security Linting (Python)
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: ['-c', 'pyproject.toml']

  # Dependency Check
  - repo: local
    hooks:
      - id: npm-audit
        name: npm audit
        entry: npm audit --audit-level moderate
        language: system
        pass_filenames: false
        files: package-lock.json

  # Type Checking
  - repo: local
    hooks:
      - id: typecheck
        name: TypeScript check
        entry: npx tsc --noEmit
        language: system
        types: [typescript]
```

### GitHub Actions

```yaml
# .github/workflows/tech-debt-gates.yml
name: Tech Debt Gates

on:
  pull_request:
    branches: [main, develop]

jobs:
  security-gate:
    name: Security Gate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Secret Detection
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: ${{ github.event.pull_request.base.sha }}
          head: ${{ github.event.pull_request.head.sha }}

      - name: Dependency Audit
        run: npm audit --audit-level moderate

      - name: SAST Scan
        uses: returntocorp/semgrep-action@v1
        with:
          config: p/security-audit p/secrets p/owasp-top-ten

  resilience-gate:
    name: Resilience Gate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Timeout Check
        run: |
          python ~/.claude/skills/tech-debt-zero/scripts/analyzers/analyze_resilience.py \
            --check timeouts --fail-on high

  quality-gate:
    name: Quality Gate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4

      - name: Install Dependencies
        run: npm ci

      - name: Type Check
        run: npx tsc --noEmit --strict

      - name: Lint
        run: npm run lint -- --max-warnings 0

      - name: Test Coverage
        run: |
          npm run test:coverage
          COVERAGE=$(cat coverage/coverage-summary.json | jq '.total.lines.pct')
          if (( $(echo "$COVERAGE < 80" | bc -l) )); then
            echo "Coverage $COVERAGE% below 80%"
            exit 1
          fi
```

### GitLab CI

```yaml
# .gitlab-ci.yml
stages:
  - security
  - quality
  - test

variables:
  SEVERITY_THRESHOLD: "high"

secret-scan:
  stage: security
  image: trufflesecurity/trufflehog:latest
  script:
    - trufflehog filesystem --directory=. --fail

dependency-check:
  stage: security
  script:
    - npm audit --audit-level moderate
  rules:
    - changes:
        - package-lock.json

security-lint:
  stage: security
  image: returntocorp/semgrep
  script:
    - semgrep --config=auto --error .

quality-check:
  stage: quality
  script:
    - npm ci
    - npm run lint -- --max-warnings 0
    - npx tsc --noEmit --strict

test-coverage:
  stage: test
  script:
    - npm ci
    - npm run test:coverage
  coverage: '/All files[^|]*\|[^|]*\s+([\d\.]+)/'
```

## Gate Severity Levels

### Default (Recommended)

| Gate | Blocks on |
|------|-----------|
| Secrets | Any finding |
| Injection | CRITICAL |
| Dependencies | HIGH+ |
| Timeout | HIGH+ |
| Type errors | Any |
| Lint | 0 warnings |
| Coverage | < 80% |

### Strict Mode (--strict)

| Gate | Blocks on |
|------|-----------|
| Secrets | Any finding |
| Injection | HIGH+ |
| Dependencies | MODERATE+ |
| Timeout | MEDIUM+ |
| Type errors | Any |
| Lint | 0 warnings |
| Coverage | < 90% |

## Customization

After generating, customize:

1. **Adjust thresholds** based on project maturity
2. **Add project-specific rules** for linting
3. **Configure exclusions** for false positives
4. **Add notifications** for failures

## Implementation

Generate configurations by reading project structure and creating appropriate YAML/JSON configs based on detected tech stack.
