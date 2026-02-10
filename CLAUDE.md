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

# Run tests (when added)
pytest tests/
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

### Phase 2: Goals & Todos (Next)
- [ ] Goal CRUD operations
- [ ] Todo CRUD operations
- [ ] Basic priority scoring algorithm
- [ ] Interactive todo picker with questionary
- [ ] Filtering and sorting for goals/todos
- [ ] Activity logging for changes

### Phase 3: Git Integration
- [ ] GitPython commit scanning
- [ ] `pm sync` command for fetching commits
- [ ] Commit message parsing for todo references (#T42)
- [ ] Activity metrics calculation
- [ ] `pm activity` and `pm commits` commands
- [ ] Auto-linking commits to todos

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

**Phase 2 Tests (TODO):**
- [ ] Create goal for project
- [ ] List goals with filtering
- [ ] Create todo linked to goal
- [ ] Priority scoring calculation
- [ ] Interactive todo picker

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
