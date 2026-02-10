# PM CLI Tutorial

A comprehensive guide to using the PM CLI tool for managing your projects, goals, and todos.

## Table of Contents

1. [Installation](#installation)
2. [Getting Started](#getting-started)
3. [Basic Workflow](#basic-workflow)
4. [Advanced Features](#advanced-features)
5. [Daily Workflows](#daily-workflows)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/yourusername/pm-cli.git
cd pm-cli

# Install in development mode
pip install -e .

# Verify installation
pm --version
```

### Shell Completion (Optional)

#### Bash
```bash
# Copy completion script
sudo cp completions/pm-completion.bash /etc/bash_completion.d/

# Or source in ~/.bashrc
echo "source /path/to/pm-cli/completions/pm-completion.bash" >> ~/.bashrc
source ~/.bashrc
```

#### Zsh
```bash
# Copy to zsh completions directory
sudo cp completions/pm-completion.zsh /usr/local/share/zsh/site-functions/_pm

# Reload completions
compinit
```

## Getting Started

### 1. Initialize Your Workspace

The first step is to initialize PM and scan your workspace for projects:

```bash
# Initialize with default workspace (~/Building/Experiments)
pm init

# Or specify a custom workspace
pm init --workspace ~/Projects
```

**What happens:**
- Creates database at `~/.pm/pm.db`
- Creates config file at `~/.pm/config.json`
- Scans workspace for projects (looks for CLAUDE.md, README.md, package.json, etc.)
- Detects git repositories

**Example output:**
```
✓ Database initialized at /Users/you/.pm/pm.db
✓ Config created at /Users/you/.pm/config.json
Scanning workspace: /Users/you/Building/Experiments
Found 12 projects:
  - EarnScreen (iOS app with git)
  - fax-snap (Web app with git)
  - SwarmInvest (Django backend with git)
  ...
✓ Workspace scan complete
```

### 2. View Your Projects

```bash
# List all projects
pm projects

# Filter by status
pm projects --status active

# Sort by priority
pm projects --sort priority
```

**Example output:**
```
┏━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ Project      ┃ Status  ┃ Priority ┃ Has Git ┃ Last Activity    ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ EarnScreen   │ active  │ 95       │ ✓       │ 2 days ago       │
│ fax-snap     │ active  │ 90       │ ✓       │ 5 days ago       │
│ SwarmInvest  │ paused  │ 70       │ ✓       │ 3 weeks ago      │
└──────────────┴─────────┴──────────┴─────────┴──────────────────┘
```

### 3. View Project Details

```bash
pm project show EarnScreen
```

**Example output:**
```
╭─────────────── EarnScreen ───────────────╮
│ Path: /Users/you/Projects/EarnScreen     │
│ Status: active                           │
│ Priority: 95                             │
│ Has Git: Yes                             │
│ Last Activity: 2 days ago                │
│                                          │
│ Description:                             │
│ iOS app for screen time management with  │
│ gamification and rewards.                │
│                                          │
│ Tech Stack: Swift, SwiftUI               │
╰──────────────────────────────────────────╯
```

## Basic Workflow

### Working with Goals

Goals represent strategic objectives for your projects.

#### Create a Goal

```bash
pm goal add EarnScreen "Complete App Store submission" \
  --category feature \
  --priority 95 \
  --target 2026-03-01 \
  --description "Prepare all assets, screenshots, and metadata for App Store review"
```

**Categories:**
- `feature` - New functionality
- `bugfix` - Bug fixes
- `refactor` - Code improvements
- `docs` - Documentation
- `ops` - Operations/deployment

#### List Goals

```bash
# All goals
pm goals

# Goals for specific project
pm goals EarnScreen

# Filter by status
pm goals --status active

# Filter by priority
pm goals --priority-min 80
```

#### View Goal Details

```bash
pm goal show 1
```

**Example output:**
```
╭────── Goal #1: Complete App Store submission ──────╮
│ Project: EarnScreen                                │
│ Category: feature                                  │
│ Priority: 95                                       │
│ Status: active                                     │
│ Target Date: 2026-03-01                           │
│                                                    │
│ Progress: 3/5 todos completed (60%)               │
│                                                    │
│ Description:                                       │
│ Prepare all assets, screenshots, and metadata     │
│ for App Store review                              │
╰────────────────────────────────────────────────────╯
```

### Working with Todos

Todos are actionable work items derived from goals.

#### Create a Todo

```bash
pm todo add EarnScreen "Prepare app screenshots" \
  --goal 1 \
  --effort M \
  --due 2026-02-15 \
  --description "Create 6.7 and 5.5 inch screenshots for App Store" \
  --tags "design,appstore"
```

**Effort sizes:**
- `S` - Small (< 2 hours)
- `M` - Medium (2-4 hours)
- `L` - Large (4-8 hours)
- `XL` - Extra Large (> 8 hours)

#### List Todos

```bash
# All open/in_progress todos
pm todos

# Todos for specific project
pm todos EarnScreen

# Top 5 by priority (what to work on next)
pm todos --next

# Show blocked todos
pm todos --blocked

# Show completed todos
pm todos --status completed
```

**Example output:**
```
Top 5 Todos by Priority:

┏━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━┓
┃ ID ┃ Project    ┃ Title                   ┃ Priority ┃ Effort  ┃ Status ┃
┡━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━┩
│ 5  │ EarnScreen │ Fix authentication bug  │ 85.8     │ M       │ in_pr… │
│ 3  │ fax-snap   │ Add PDF export feature  │ 71.5     │ S       │ open   │
│ 7  │ EarnScreen │ Write API documentation │ 68.2     │ L       │ open   │
└────┴────────────┴─────────────────────────┴──────────┴─────────┴────────┘
```

#### Start Working on a Todo

```bash
pm todo start 5
```

This marks the todo as "in_progress" and applies a 1.2x priority boost (sticky priority).

#### Complete a Todo

```bash
pm todo complete 5
```

**Example output:**
```
🎉 Todo #5 marked as completed!
   Priority recalculated for EarnScreen project
```

#### Block a Todo

If a todo is blocked by another:

```bash
pm todo block 3 --by 5
```

This marks todo #3 as blocked by todo #5 and applies a 0.5x priority reduction.

## Advanced Features

### CLAUDE.md Integration

If your projects have CLAUDE.md files with structured documentation, PM can automatically import goals.

#### Import Goals from CLAUDE.md

```bash
# Interactive import (shows preview, asks for confirmation)
pm import-claude-md EarnScreen

# Auto-import without confirmation
pm import-claude-md EarnScreen --auto-import
```

**What gets imported:**
- Goals from "Next Steps", "TODO", "Roadmap", or "Planned Features" sections
- Categories are automatically inferred (feature/bugfix/refactor/docs/ops)
- Priorities are suggested based on keywords (critical, urgent, important, etc.)

**Example CLAUDE.md structure:**
```markdown
# EarnScreen

## Next Steps

- [ ] Complete App Store submission
- [ ] Fix authentication bug
- [ ] Add push notifications
```

### Git Integration

PM can track git commits and link them to todos automatically.

#### Sync Git Commits

```bash
# Sync specific project
pm sync EarnScreen

# Sync all projects
pm sync --all

# Limit commits per project
pm sync --limit 100
```

#### Link Commits to Todos

In your commit messages, reference todos using these patterns:
- `#T42` or `#42` - Links commit to todo #42
- `fixes #42`, `closes #42`, `resolves #42`, `completes #42` - Links AND auto-completes todo #42

**Example commit:**
```bash
git commit -m "fix: resolve authentication redirect issue (fixes #5)"
```

This will:
1. Link the commit to todo #5
2. Automatically mark todo #5 as completed
3. Update project activity timestamp

#### View Project Activity

```bash
# Show 30-day activity timeline
pm activity EarnScreen

# Show last 7 days
pm activity EarnScreen --days 7

# Since specific date
pm activity EarnScreen --since 2026-02-01
```

#### View Commits

```bash
# Recent commits
pm commits EarnScreen

# Filter by author
pm commits EarnScreen --author "Carlo"

# Filter by date
pm commits EarnScreen --since 2026-02-01

# Show more commits
pm commits EarnScreen --limit 50
```

### Priority Management

PM uses a multi-factor algorithm to calculate priority scores (0-100):

**Factors:**
- 25% Goal Priority (higher goal priority = higher todo priority)
- 15% Project Priority (active projects get boost)
- 15% Age Urgency (older todos score higher)
- 20% Deadline Pressure (closer deadlines score higher)
- 10% Effort Value (quick wins favored: S=80, M=60, L=40, XL=20)
- 10% Git Activity (recent commits boost priority)
- 5% Blocking Impact (each blocked todo adds points)

**Adjustments:**
- Blocked todos: score × 0.5
- In-progress todos: score × 1.2 (sticky priority)

#### Recalculate Priorities

```bash
# Recalculate all priorities
pm prioritize

# Recalculate for specific project
pm prioritize EarnScreen
```

### Analytics & Dashboards

#### View Project Metrics

```bash
# Basic metrics dashboard
pm metrics EarnScreen

# Detailed metrics with trends
pm metrics EarnScreen --detailed
```

**Example output:**
```
╭──────────── EarnScreen Metrics ────────────╮
│                                            │
│ Health Score: 66.3/100 (Good)             │
│ Velocity: 0.14 todos/day                  │
│ Completion Rate: 60.0%                    │
│                                            │
│ Todos:                                     │
│   Open: 2                                  │
│   In Progress: 1                           │
│   Blocked: 0                               │
│   Completed: 3                             │
│                                            │
│ Goals:                                     │
│   Active: 2                                │
│   Completed: 1                             │
│                                            │
│ Upcoming Deadlines:                        │
│   #5: App screenshots (3 days)            │
│   #7: API docs (12 days)                  │
╰────────────────────────────────────────────╯
```

#### Generate Reports

```bash
# Markdown report to stdout
pm report EarnScreen

# Save to file
pm report EarnScreen --format markdown --output report.md

# HTML report
pm report EarnScreen --format html --output report.html
```

### Export & Backup

#### Export Project Data

```bash
# Export single project to JSON
pm export EarnScreen --output earnscreen-backup.json
```

**Export includes:**
- Project metadata
- All goals with relationships
- All todos with tags and blocked_by
- All commits with stats

#### Backup All Projects

```bash
# Backup to default location (~/.pm/backups/)
pm backup

# Custom output directory
pm backup --output ~/Backups/pm-data/
```

Creates separate JSON files for each project.

## Daily Workflows

### Interactive Start Workflow

The `pm start` command provides an interactive workflow to quickly start working:

```bash
pm start
```

**Steps:**
1. Select a project from list (sorted by recent activity)
2. Select a todo from prioritized list
3. Automatically marks todo as "in_progress"
4. Shows todo details

### Interactive Planning

Create goals and todos interactively:

```bash
pm plan EarnScreen
```

**Steps:**
1. Optionally import goals from CLAUDE.md
2. Create new goals with interactive prompts
3. Add todos for each goal
4. Set priorities and deadlines

### Daily Standup

Get a daily overview and plan your work:

```bash
# General standup (top 5 projects)
pm standup

# Project-specific standup
pm review --project EarnScreen
```

**Output includes:**
1. Project health scores
2. Top priority todos
3. Overdue items
4. Recent activity
5. Action menu:
   - Start next todo
   - Review metrics
   - View activity
   - Exit

### Sync and Prioritize

Daily workflow command to sync git commits and recalculate priorities:

```bash
# All projects
pm sync-and-prioritize

# Specific project
pm sync-and-prioritize EarnScreen
```

## Best Practices

### 1. Start Each Day with Standup

```bash
pm standup
```

This gives you a clear overview of what needs attention and helps you decide what to work on.

### 2. Use the Interactive Start Workflow

Instead of manually looking for todos:

```bash
pm start
```

Let PM guide you to the highest priority work.

### 3. Reference Todos in Commit Messages

Always link commits to todos:

```bash
git commit -m "feat: add user authentication (#T12)"
```

This creates a complete audit trail of your work.

### 4. Review Metrics Weekly

```bash
pm metrics EarnScreen --detailed
```

Track your velocity and identify stalled projects.

### 5. Import Goals from CLAUDE.md

When starting a new project:

```bash
pm project add ~/Projects/NewProject
pm import-claude-md NewProject
```

This automatically populates your backlog.

### 6. Block Todos Explicitly

If you can't start a todo:

```bash
pm todo block 7 --by 5
```

This helps explain why work isn't progressing.

### 7. Use Appropriate Effort Sizes

Be realistic about effort:
- S: Quick fixes, small changes
- M: Feature additions, moderate bugs
- L: Complex features, refactoring
- XL: Major features, architectural changes

Small todos score higher in priority (quick wins).

### 8. Set Target Dates for Goals

```bash
pm goal add MyProject "Launch MVP" --target 2026-03-31
```

This helps deadline pressure factor in priority scoring.

### 9. Regular Backups

```bash
# Add to cron or run weekly
pm backup --output ~/Backups/pm/$(date +%Y-%m-%d)/
```

### 10. Keep Projects Active or Paused

Update project status to reflect reality:

```bash
pm project update OldProject --status archived
pm project update ActiveProject --status active --priority 90
```

This focuses your standup reviews on relevant work.

## Troubleshooting

### Database Issues

**Problem:** Database is corrupted or behaving strangely

**Solution:** Reset the database (WARNING: deletes all data)
```bash
rm ~/.pm/pm.db
pm init
```

**Better solution:** Restore from backup
```bash
rm ~/.pm/pm.db
pm init
# Then manually import your backup JSON files
```

### Git Sync Not Working

**Problem:** `pm sync` doesn't find commits

**Solution:** Check git repository
```bash
cd /path/to/project
git log --oneline -10  # Verify commits exist
pm sync ProjectName --limit 10
```

### Priority Scores Seem Wrong

**Problem:** Priorities don't match expectations

**Solution:**
1. Check factors that affect priority:
   ```bash
   pm todo show 5  # View todo details
   ```
2. Manually recalculate:
   ```bash
   pm prioritize
   ```
3. Adjust project or goal priorities:
   ```bash
   pm project update MyProject --priority 95
   pm goal update 3 --priority 90
   ```

### Import from CLAUDE.md Failing

**Problem:** Goals not imported from CLAUDE.md

**Solution:** Check CLAUDE.md structure
```bash
cat /path/to/project/CLAUDE.md | grep -A 10 "Next Steps"
```

Must have sections titled:
- "Next Steps"
- "TODO"
- "Roadmap"
- "Planned Features"

With list items:
- `- [ ] Item` (checkbox)
- `- Item` (bullet)
- `1. Item` (numbered)

### Shell Completion Not Working

**Problem:** Tab completion doesn't work

**Solution for Bash:**
```bash
source /path/to/pm-cli/completions/pm-completion.bash
# Add to ~/.bashrc for persistence
```

**Solution for Zsh:**
```bash
# Ensure completion script is in $fpath
echo $fpath
# Copy script to one of those directories
sudo cp completions/pm-completion.zsh /usr/local/share/zsh/site-functions/_pm
# Reload completions
rm -f ~/.zcompdump; compinit
```

## Next Steps

- Check out the [README.md](README.md) for command reference
- Review the [CONTRIBUTING.md](.github/CONTRIBUTING.md) if you want to contribute
- Report issues on [GitHub Issues](https://github.com/yourusername/pm-cli/issues)

Happy project managing! 🚀
