# PM - Project Management CLI Tool

A language-agnostic CLI tool for managing project goals, todos, and priorities across multiple projects.

## Features

- 📦 Track multiple projects in your workspace
- 🎯 Set strategic goals for each project
- ✅ Create and prioritize actionable todos
- 📊 Git integration for activity tracking
- 📈 Analytics and metrics dashboards
- 🔍 Intelligent priority scoring
- 🎨 Beautiful terminal output with Rich

## Installation

```bash
cd ~/Building/Experiments/pm
pip install -e .
```

After installation, the `pm` command will be available globally.

## Quick Start

```bash
# Initialize database and scan workspace
pm init

# List all projects
pm projects

# View project details
pm project show EarnScreen

# Add a new project manually
pm project add /path/to/project --name MyProject --priority 80

# Update project status
pm project update MyProject --status active --priority 90
```

## Commands

### Initialization

```bash
pm init                    # Initialize database and scan workspace
pm init --workspace PATH   # Scan custom workspace directory
```

### Project Management

```bash
pm projects                           # List all projects
pm projects --status active           # Filter by status
pm projects --sort priority           # Sort by priority, activity, or name

pm project add PATH                   # Add new project
pm project show NAME                  # Show project details
pm project update NAME --status paused --priority 80
```

### Goals

```bash
pm goal add PROJECT "Goal title" --priority 90 --target 2026-03-01
pm goals                              # List all goals
pm goals PROJECT                      # List project goals
pm goal show GOAL_ID                  # Show detailed goal info
pm goal update GOAL_ID --status completed
```

### Todos

```bash
pm todo add PROJECT "Task title" --effort M --due 2026-02-15
pm todos                              # List all open todos
pm todos --next                       # Top 5 by priority
pm todos --blocked                    # Show blocked todos
pm todo show TODO_ID                  # Show detailed todo info
pm todo start TODO_ID                 # Mark as in progress
pm todo complete TODO_ID              # Mark as completed
pm todo block TODO_ID --by BLOCKER_ID # Mark as blocked
```

### Priority Management

```bash
pm prioritize                         # Recalculate all priorities
pm prioritize PROJECT                 # Recalculate for specific project
```

### Git Integration (Coming Soon)

```bash
pm sync PROJECT                       # Sync git commits
pm activity PROJECT                   # Show recent activity
pm commits PROJECT --since "7 days ago"
```

### Analytics (Coming Soon)

```bash
pm metrics PROJECT                    # Show project metrics
pm review                             # Daily standup helper
pm prioritize                         # Recalculate all priorities
```

## Configuration

Configuration is stored in `~/.pm/config.json`. Default settings:

```json
{
  "workspace_path": "~/Building/Experiments",
  "default_priority": 50,
  "auto_sync_on_review": true,
  "show_completed_todos": false
}
```

## Database

Database is stored at `~/.pm/pm.db` (SQLite). You can backup the database:

```bash
# Automatic backup
python -c "from pm.db import get_db_manager; print(get_db_manager().backup_db())"
```

## Development Status

**Phase 1 (Complete):**
- ✅ Project structure and package setup
- ✅ SQLAlchemy models and database schema
- ✅ Basic CLI with Click
- ✅ Project management commands
- ✅ Rich terminal output

**Phase 2 (Complete):**
- ✅ Goals CRUD (add, list, show, update)
- ✅ Todos CRUD (add, list, show, start, complete, block)
- ✅ Multi-factor priority scoring algorithm
- ✅ Filtering and sorting
- ✅ Effort estimation and deadline tracking
- ✅ 16 passing tests (100% coverage of core features)

**Phase 3-6 (Coming Soon):**
- Git integration and commit tracking
- Analytics and metrics dashboards
- CLAUDE.md parsing
- Interactive workflows

## Tech Stack

- **Python 3.10+**
- **Click** - CLI framework
- **SQLAlchemy** - ORM and database
- **Rich** - Beautiful terminal output
- **GitPython** - Git integration
- **Pydantic** - Data validation

## License

MIT
