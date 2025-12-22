---
name: skill-creator
description: "Creates new Claude Code skills. Use when user wants to create reusable workflows with scripts and references."
---

# Skill Creator

Creates modular skill packages that extend Claude's capabilities.

## What are Skills?

Skills are packages containing:
- **SKILL.md** - Main instructions
- **scripts/** - Executable Python/JS files
- **references/** - Documentation and schemas
- **assets/** - Templates and static files

## When to Use

- User has a repeating workflow to automate
- User wants to bundle scripts with instructions
- User needs domain-specific knowledge loaded on demand

## Creation Process

### Step 1: Understand the Workflow

Ask user:
1. What task does this skill perform?
2. What triggers should activate it?
3. Are there scripts that should be included?
4. What reference docs are needed?

### Step 2: Create Folder Structure

```
.claude/skills/{skill-name}/
├── SKILL.md              # Required: Main instructions
├── scripts/              # Optional: Executable scripts
│   └── main_script.py
├── references/           # Optional: Documentation
│   └── schema.md
└── assets/              # Optional: Templates, images
    └── template.html
```

### Step 3: Write SKILL.md

```markdown
---
name: {skill-name}
description: "{Description}. Use when {trigger condition}."
---

# {Skill Name}

Brief overview of what this skill does.

## Workflow

### Step 1: {First Step}
{Instructions}

### Step 2: {Second Step}
{Instructions}

## Scripts

- `scripts/main_script.py` - {What it does}

## References

- `references/schema.md` - {What it contains}

## Output

{What this skill produces}
```

### Step 4: Create Supporting Files

For scripts:
```python
#!/usr/bin/env python3
"""
Script description
Usage: python scripts/main_script.py [args]
"""
import sys

def main():
    # Implementation
    pass

if __name__ == "__main__":
    main()
```

For references:
```markdown
# Reference Title

## Schema
{Data structures}

## Examples
{Usage examples}
```

## Design Principles

1. **Conciseness** - Only include what Claude doesn't know
2. **Progressive Disclosure** - Load details only when needed
3. **Single Responsibility** - One skill, one purpose
4. **Reusability** - Design for multiple projects

## Examples

### PDF Processor Skill
```
.claude/skills/pdf-processor/
├── SKILL.md
├── scripts/
│   ├── extract_text.py
│   └── extract_images.py
└── references/
    └── pdf-structure.md
```

### API Client Skill
```
.claude/skills/api-client/
├── SKILL.md
├── scripts/
│   └── make_request.py
└── references/
    ├── endpoints.md
    └── auth-schema.md
```
