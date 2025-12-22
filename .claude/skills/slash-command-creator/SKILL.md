---
name: slash-command-creator
description: "Creates custom slash commands. Use when user wants to create shortcut commands like /review, /deploy, /test."
---

# Slash Command Creator

Creates custom slash commands for quick task execution.

## What are Slash Commands?

Slash commands are markdown files that expand into prompts when invoked with `/command-name`.

## Location

- Project: `.claude/commands/{command-name}.md`
- User: `~/.claude/commands/{command-name}.md`

## Creation Process

### Step 1: Identify the Command

Ask user:
1. What should `/command` do?
2. Does it need arguments? (`$ARGUMENTS`)
3. Should it include file contents? (`@file`)
4. Project-specific or global?

### Step 2: Create Command File

`.claude/commands/{command-name}.md`:

```markdown
---
description: "Brief description shown in /help"
---

# Command prompt goes here

{Instructions that will be sent as a prompt}

## Arguments
$ARGUMENTS - captured from user input after command

## Files
@path/to/file.py - will include file contents
```

### Step 3: Test

Run `/command-name` in Claude Code to verify it works.

## Special Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `$ARGUMENTS` | Text after command | `/review fix the bug` → "fix the bug" |
| `@path/file` | Include file contents | `@app.py` includes app.py |
| `@folder/` | Include folder listing | `@src/` lists src/ contents |

## Examples

### /review - Code Review
```markdown
---
description: "Review recent code changes"
---

Review the following code for:
1. Bugs and logic errors
2. Security vulnerabilities
3. Performance issues
4. Code style

Focus on: $ARGUMENTS

Files to review:
@app.py
```

### /test - Run Tests
```markdown
---
description: "Run tests and report results"
---

Run the project tests and report:
1. Which tests passed/failed
2. Coverage percentage
3. Suggestions for fixing failures

Test focus: $ARGUMENTS
```

### /deploy - Deployment
```markdown
---
description: "Deploy to specified environment"
---

Deploy the application to: $ARGUMENTS

Steps:
1. Run tests first
2. Build the project
3. Deploy to target environment
4. Verify deployment

Current config:
@railway.json
```

### /church - Church Bulletin
```markdown
---
description: "Work on church bulletin system"
---

I'm working on the church bulletin HTML generation system.

Current request: $ARGUMENTS

Key files:
@church_html_generator.py
@vision_ocr.py

Reference the quality standards in CLAUDE.md.
```

### /fix - Quick Fix
```markdown
---
description: "Fix an issue in specified file"
---

Fix the following issue: $ARGUMENTS

Constraints:
- Make minimal changes
- Don't add features
- Preserve existing behavior
- Test the fix
```

## Best Practices

1. Keep commands focused on one task
2. Include relevant files with @ syntax
3. Use $ARGUMENTS for flexibility
4. Write clear descriptions for /help
5. Test commands before sharing
