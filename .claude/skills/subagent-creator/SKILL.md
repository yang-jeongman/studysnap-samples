---
name: subagent-creator
description: "Creates new Claude Code sub-agents. Use when user wants to create a specialized agent for specific tasks."
---

# Subagent Creator

Creates specialized Claude Code sub-agents with custom configurations.

## When to Use
- User asks to "create an agent for X"
- User wants to automate repetitive prompts
- User needs a specialized assistant for specific domain

## Creation Process

### Step 1: Gather Requirements
Ask user:
1. What should this agent do?
2. When should it be triggered?
3. What tools does it need? (Read, Write, Edit, Bash, Grep, Glob, WebFetch)
4. What model? (haiku=fast/cheap, sonnet=balanced, opus=best)

### Step 2: Generate Agent File

Create `.claude/agents/{agent-name}.md`:

```markdown
---
name: {kebab-case-name}
description: "{Clear description}. Use PROACTIVELY when {trigger condition}."
tools:
  - Tool1
  - Tool2
model: {haiku|sonnet|opus}
---

# Role
{What this agent is}

# When Invoked
1. {First action}
2. {Second action}
3. {Third action}

# Responsibilities
- {Responsibility 1}
- {Responsibility 2}
- {Responsibility 3}

# Guidelines
- {Guideline 1}
- {Guideline 2}
- {Guideline 3}

# Output Format
{How results should be presented}
```

### Step 3: Validate and Save
- Check name follows kebab-case
- Ensure description includes trigger condition
- Verify tools are valid
- Save to `.claude/agents/` directory

## Tool Options

| Tool | Description | When to Include |
|------|-------------|-----------------|
| Read | Read files | Always for code work |
| Write | Create files | When creating content |
| Edit | Modify files | When editing code |
| Bash | Run commands | For system operations |
| Grep | Search content | For code search |
| Glob | Find files | For file discovery |
| WebFetch | Fetch URLs | For web scraping |
| WebSearch | Search web | For research |

## Model Selection

- **haiku**: Simple tasks, fast response, low cost
- **sonnet**: Most tasks, balanced performance
- **opus**: Complex reasoning, highest quality

## Examples

### Research Agent
```markdown
---
name: tech-researcher
description: "Researches technical topics. Use when user asks about new technologies, libraries, or best practices."
tools:
  - WebSearch
  - WebFetch
  - Read
model: sonnet
---
```

### File Cleanup Agent
```markdown
---
name: cleanup-agent
description: "Cleans up project files. Use when user asks to remove temp files, organize folders, or clean up outputs."
tools:
  - Glob
  - Bash
  - Read
model: haiku
---
```
