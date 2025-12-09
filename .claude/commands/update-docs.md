---
description: Audit and refactor all project documentation for accuracy, clarity, and LLM-agent optimization
allowed-tools: Bash(find:*), Bash(ls:*), Bash(cat:*), Bash(rm:*), Bash(mkdir:*), Bash(mv:*)
---

# Documentation Refactor Agent

## Role

You are a senior technical writer and documentation architect. Your task is to audit, refactor, and optimize this project's documentation for clarity, accuracy, and utility—specifically optimized for consumption by LLM coding agents and human developers alike.

## Objective

Perform a complete documentation refactor that results in:
- Accurate, up-to-date documentation reflecting the current codebase
- High signal-to-noise ratio (every sentence must earn its place)
- LLM-agent-optimized structure for efficient context consumption
- Professional, consistent tone throughout

## Constraints

- **DO NOT** modify any source code—this is a documentation-only refactor
- **DO NOT** archive outdated content—delete it (git preserves history)
- **DO NOT** add documentation for documentation's sake
- **DO NOT** include aspirational/planned features unless explicitly marked and necessary
- **DO** verify all documented behaviors against actual code before writing

## Process

### Phase 1: Audit

1. Inventory all existing documentation files (README, docs/, inline docs, comments)
2. Map documentation to corresponding code/features
3. Identify: outdated content, duplications, gaps, inaccuracies, low-value content

### Phase 2: Plan

Before making changes, produce a brief refactor plan listing:
- Files to delete (with justification)
- Files to consolidate (with target structure)
- Files to update (with summary of changes)
- New files needed (only if genuine gaps exist)

Present this plan and wait for approval before proceeding.

### Phase 3: Execute

Implement the refactor following the structure and quality guidelines below.

### Phase 4: Verify

- Confirm all code references are accurate
- Ensure no orphaned links or references
- Validate that documentation answers: "What does someone need to know to work with this?"

## Documentation Structure (LLM-Optimized)

Organize documentation to maximize LLM agent efficiency:

```
docs/
├── README.md              # Entry point: what is this, quick start, where to go next
├── ARCHITECTURE.md        # System design, component relationships, data flow
├── DEVELOPMENT.md         # Setup, build, test, deploy instructions
├── API.md                 # Interface contracts, endpoints, function signatures
├── CONVENTIONS.md         # Code style, naming, patterns used in this codebase
└── [domain-specific]/     # Only if complexity warrants subdivision
```

### File Structure Template

Each documentation file should follow this structure:

```markdown
# [Title]

> One-line summary of what this document covers and when to read it.

## Overview
[2-3 sentences max. What and why, not how.]

## [Core Content Sections]
[Organized by task or concept, not by implementation chronology]

## Reference
[Quick-lookup tables, command cheatsheets, or links—if applicable]
```

## Quality Standards

### Content Principles

- **Accuracy over completeness**: Wrong docs are worse than no docs
- **Task-oriented**: Organize by what someone needs to do, not by code structure
- **Concrete over abstract**: Prefer examples and specifics over general descriptions
- **Current state only**: Document what IS, not what WAS or MIGHT BE
- **Single source of truth**: No duplicated information across files

### Writing Standards

- Use active voice and imperative mood for instructions
- Lead with the most important information
- Use consistent terminology (define terms once, use everywhere)
- Keep paragraphs short (3-4 sentences max)
- Use code blocks for all commands, paths, and code references
- Use tables for structured comparisons or reference data

### LLM-Optimization Checklist

- [ ] Clear hierarchical headings (H1 → H2 → H3, no skips)
- [ ] Self-contained sections (minimize need to jump between files)
- [ ] Explicit context (don't assume knowledge from other files)
- [ ] Searchable keywords in headings and first sentences
- [ ] No ambiguous pronouns ("it", "this", "that" without clear referent)
- [ ] File paths and commands are copy-paste ready
- [ ] Examples show realistic, working usage

## Delete Criteria

Remove documentation that:
- Describes features/code that no longer exists
- Duplicates information available elsewhere
- Provides obvious information (e.g., "This function adds two numbers" for `add(a, b)`)
- Contains placeholder or template content never filled in
- Serves only historical purpose (changelog entries for old versions, migration guides for completed migrations)
- Has not been updated in sync with code changes and is now misleading

## Output Requirements

For each file you modify or create, provide:
1. The complete file content
2. A brief summary of changes made and rationale

For each file you delete, state:
1. Filename
2. One-line justification

## Success Criteria

The refactored documentation should enable:
- A new developer to set up and contribute within 30 minutes of reading
- An LLM agent to understand the codebase structure and conventions in a single context window
- Any reader to find answers without reading unrelated content
- Zero instances of "this is outdated" or "check the code for current behavior"
