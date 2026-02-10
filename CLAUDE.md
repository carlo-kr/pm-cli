# PM - Project Management CLI Tool

## Overview

A language-agnostic CLI tool for managing project goals, todos, and priorities across multiple projects in a workspace. Built with Python, SQLite, and designed to integrate with git for activity tracking.

## Commands

### Development
```bash
# Install in development mode
cd ~/Building/Experiments/pm
python3 -m pip install -e .

# Run CLI (if not on PATH)
/Library/Frameworks/Python.framework/Versions/3.12/bin/pm --version

# Run tests
pytest tests/                         # All tests
pytest tests/test_priority.py -v     # Priority algorithm tests
pytest tests/ --cov=pm --cov-report=html  # With coverage
```

### Database Management
```bash
# Database location: ~/.pm/pm.db
# Config location: ~/.pm/config.json

# Backup database
python3 -c "from pm.db import get_db_manager; print(get_db_manager().backup_db())"

# Reset database (for development)
rm ~/.pm/pm.db && pm init
```

### Complete Command Reference

#### Initialization
```bash
pm init                               # Initialize DB and scan workspace
pm init --workspace /path/to/dir      # Scan custom directory
```

#### Project Management
```bash
pm projects                           # List all projects
pm projects --status active           # Filter by status
pm projects --sort priority           # Sort by priority/activity/name
pm project add /path/to/project       # Add new project
pm project show EarnScreen            # Show project details
pm project update EarnScreen --priority 95 --status active
```

#### Goal Management
```bash
pm goals                              # List all goals
pm goals EarnScreen                   # List goals for project
pm goals --status active              # Filter by status
pm goals --priority-min 70            # Filter by minimum priority

pm goal add EarnScreen "Complete MVP" \
  --category feature \
  --priority 90 \
  --target 2026-03-01 \
  --description "Full description here"

pm goal show 1                        # Show goal details with progress
pm goal update 1 --status completed   # Update goal properties
```

#### Todo Management
```bash
pm todos                              # List all open/in_progress todos
pm todos EarnScreen                   # List todos for project
pm todos --next                       # Top 5 by priority
pm todos --blocked                    # Show blocked todos
pm todos --status completed           # Show completed todos
pm todos --goal 1                     # Filter by goal

pm todo add EarnScreen "Fix auth bug" \
  --goal 1 \
  --effort M \
  --due 2026-02-15 \
  --description "Detailed description" \
  --tags "bug,urgent"

pm todo show 5                        # Show todo details
pm todo start 5                       # Mark as in_progress (1.2x priority)
pm todo complete 5                    # Mark as completed
pm todo block 3 --by 5                # Mark todo 3 as blocked by todo 5
```

#### Priority Management
```bash
pm prioritize                         # Recalculate all priorities
pm prioritize EarnScreen              # Recalculate for specific project
```

#### Git Integration
```bash
pm sync EarnScreen                    # Sync commits for project
pm sync --all                         # Sync all projects with git repos
pm sync --limit 100                   # Limit commits per project

pm commits EarnScreen                 # Show recent commits
pm commits EarnScreen --limit 20      # Show more commits
pm commits EarnScreen --author "Carlo" # Filter by author
pm commits EarnScreen --since 2026-02-01 # Filter by date

pm activity EarnScreen                # Show 30-day activity timeline
pm activity EarnScreen --days 7       # Show last 7 days
pm activity EarnScreen --since 2026-02-01 # Since specific date

pm sync-and-prioritize                # Sync + recalculate (daily workflow)
pm sync-and-prioritize EarnScreen     # For specific project
```

## Architecture

| Component | Technology | Purpose |
|-----------|-----------|---------|
| CLI Framework | Click | Command-line interface and argument parsing |
| Database | SQLite + SQLAlchemy | Local data persistence with ORM |
| Terminal UI | Rich | Beautiful formatted output (tables, panels, colors) |
| Git Integration | GitPython | Repository scanning and commit tracking |
| Data Validation | Pydantic | Schema validation and configuration |
| Date Parsing | python-dateutil | Flexible date/time parsing |

## Key Models

**Database Schema (models.py):**
- `Project` - Workspace projects with status, priority, metadata
- `Goal` - Strategic objectives linked to projects
- `Todo` - Actionable work items with priority scoring
- `Commit` - Git commits for activity correlation
- `Metric` - Time-series analytics data
- `ActivityLog` - Audit trail for changes

**Relationships:**
- Project → Goals (1:N)
- Project → Todos (1:N)
- Project → Commits (1:N)
- Goal → Todos (1:N, optional)
- Goal → Sub-goals (self-referential)

## Implementation Status

### Phase 1: Core Foundation ✅ (Complete)
- [x] Project structure and package setup
- [x] SQLAlchemy models with proper relationships
- [x] Database manager with session handling
- [x] Basic Click CLI with subcommands
- [x] Project management commands (add, list, show, update)
- [x] Rich terminal output with tables and panels
- [x] Configuration management (~/.pm/config.json)
- [x] Workspace scanning with project detection

### Phase 2: Goals & Todos ✅ (Complete)
- [x] Goal CRUD operations (add, list, show, update)
- [x] Todo CRUD operations (add, list, show, start, complete, block)
- [x] Multi-factor priority scoring algorithm
- [x] Filtering and sorting for goals/todos
- [x] Status management (open, in_progress, blocked, completed)
- [x] Effort estimation (S/M/L/XL) with quick-win scoring
- [x] Deadline tracking with urgency calculation
- [x] Blocking relationships between todos
- [x] Automatic priority recalculation
- [ ] Interactive todo picker with questionary (deferred to Phase 5)
- [ ] Activity logging for changes (deferred to Phase 4)

### Phase 3: Git Integration ✅ (Complete)
- [x] GitPython commit scanning with GitScanner class
- [x] `pm sync` command for fetching commits (single project or --all)
- [x] Commit message parsing for todo references (#T42, #42, fixes #42, etc.)
- [x] Activity metrics calculation (insertions, deletions, files changed)
- [x] `pm activity` command with timeline visualization
- [x] `pm commits` command with filtering by author and date
- [x] Auto-linking commits to todos (bidirectional)
- [x] Auto-completion of todos when commit has completion keywords
- [x] Project last_activity_at tracking
- [x] `pm sync-and-prioritize` workflow command

### Phase 4: Analytics & Dashboards
- [ ] Metrics calculator with time-series tracking
- [ ] `pm metrics` dashboard with Rich visualizations
- [ ] Trend analysis (velocity, health scores)
- [ ] `pm review` command (daily standup helper)
- [ ] Report generation (markdown, HTML)
- [ ] Enhanced priority algorithm with git activity

### Phase 5: Advanced Features
- [ ] CLAUDE.md parsing and automatic import
- [ ] Interactive workflows (`pm start`, `pm plan`, `pm standup`)
- [ ] Blocked todo dependency tracking
- [ ] Export/import for backup (JSON)
- [ ] Shell completion (bash/zsh)

### Phase 6: Polish & Distribution
- [ ] PyPI packaging
- [ ] Comprehensive test suite (pytest, >80% coverage)
- [ ] Complete documentation
- [ ] GitHub Actions CI/CD
- [ ] Tutorial and examples

## Technical Notes

### SQLAlchemy Best Practices
- **Reserved names**: Avoid `metadata` as column name (reserved by DeclarativeBase). Use `extra_data` instead.
- **Session management**: Always extract data within session context to avoid DetachedInstanceError:
  ```python
  with db.get_session() as session:
      projects = session.query(Project).all()
      # Extract data to dicts before session closes
      data = [{k: getattr(p, k) for k in ['name', 'status']} for p in projects]
  # Now safe to use data
  ```

### Project Detection
Projects are auto-detected during `pm init` by looking for:
- CLAUDE.md or README.md files
- Package managers: package.json, requirements.txt, pyproject.toml, Cargo.toml, go.mod, pom.xml
- Build configs: project.yml (XcodeGen)
- Git repositories (.git directory)

### Priority Scoring Algorithm (Phase 2)
Multi-factor weighted scoring (0-100):
```
Priority = 0.25×GoalPriority + 0.15×ProjectPriority + 0.15×AgeUrgency
         + 0.20×DeadlinePressure + 0.10×EffortValue + 0.10×GitActivity
         + 0.05×BlockingImpact
```

## Configuration

Default config (~/.pm/config.json):
```json
{
  "workspace_path": "~/Building/Experiments",
  "default_priority": 50,
  "auto_sync_on_review": true,
  "show_completed_todos": false,
  "todo_picker_limit": 10,
  "priority_weights": {
    "goal_priority": 0.25,
    "project_priority": 0.15,
    "age_urgency": 0.15,
    "deadline_pressure": 0.20,
    "effort_value": 0.10,
    "git_activity_boost": 0.10,
    "blocking_impact": 0.05
  }
}
```

## Testing Checklist

✅ **Phase 1 Tests:**
- [x] `pm init` - Creates database and scans workspace (found 12 projects)
- [x] `pm projects` - Lists all projects with Rich table formatting
- [x] `pm project show EarnScreen` - Displays project details in panel
- [x] `pm project update EarnScreen --priority 95` - Updates project properties
- [x] Projects sorted by priority correctly

✅ **Phase 2 Tests:**
- [x] `pm goal add EarnScreen "Complete App Store submission"` - Creates goal with priority 95
- [x] `pm goals` - Lists all goals with colored categories and status
- [x] `pm goal show 1` - Shows goal details with progress (1 completed / 2 total todos)
- [x] `pm todo add EarnScreen "Write app description" --effort S --due 2026-02-12` - Creates todo with priority score 71.5
- [x] `pm todos --next` - Shows top 5 prioritized todos
- [x] `pm todo start 2` - Marks todo as in_progress, priority increased to 85.8 (1.2x boost)
- [x] `pm todo complete 2` - Marks todo as completed
- [x] `pm todo block 1 --by 3` - Marks todo as blocked, priority reduced to 33.2 (0.5x reduction)
- [x] `pm todos --blocked` - Shows blocked todos
- [x] Priority scoring validates: effort (S>M>L>XL), deadlines (closer=higher), age (older=higher)
- [x] 16 unit tests passing (models, utils, priority algorithm)

✅ **Phase 3 Tests:**
- [x] `pm sync EarnScreen` - Syncs 4 commits from git repository
- [x] `pm commits EarnScreen` - Lists recent commits with stats and linked todos
- [x] `pm activity EarnScreen --days 7` - Shows daily activity timeline
- [x] `pm sync --all` - Syncs all projects (28 commits from 4 projects)
- [x] Commit with `#T5` reference - Auto-links to todo #5
- [x] Commit with `complete #5` - Auto-completes todo and sets completion timestamp
- [x] `pm todo show 5` - Shows linked commits in todo details
- [x] Todo references parsed: #T42, #42, fixes #42, closes #42, resolves #42, todo: #42
- [x] Completion keywords work: fix, fixes, close, closes, resolve, resolves, complete, completes
- [x] 13 new unit tests passing (git integration, commit parsing, stats)

## Next Steps

1. **Implement Goals Management** (Phase 2)
   - Add `pm goal add/list/show/update` commands
   - Goal categories and status validation
   - Sub-goal relationships

2. **Implement Todos Management** (Phase 2)
   - Add `pm todo add/list/show/update/start/complete` commands
   - Effort estimation (S/M/L/XL)
   - Blocking relationships

3. **Priority Scoring** (Phase 2)
   - Implement priority calculator in `priority.py`
   - `pm prioritize` command to recalculate all priorities
   - `pm todos --next` to show top-priority todos

4. **Git Integration** (Phase 3)
   - Implement commit scanner with GitPython
   - Parse commit messages for todo references
   - Update project.last_activity_at on sync

## Dependencies

```
click>=8.1.0          # CLI framework
sqlalchemy>=2.0.0     # ORM and database
gitpython>=3.1.0      # Git integration
rich>=13.0.0          # Terminal UI
pydantic>=2.0.0       # Data validation
alembic>=1.12.0       # Database migrations (future)
questionary>=2.0.0    # Interactive prompts
python-dateutil>=2.8.0 # Date parsing
```
