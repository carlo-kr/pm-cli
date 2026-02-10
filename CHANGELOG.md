# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-02-10

### Added

#### Phase 1: Core Foundation
- Initial project structure with SQLAlchemy ORM and SQLite database
- 6-table database schema (projects, goals, todos, commits, metrics, activity_log)
- Click CLI framework with subcommands
- Rich terminal output with tables, panels, and colors
- Project management commands: `pm init`, `pm projects`, `pm project add/show/update`
- Workspace scanning with automatic project detection
- Configuration management at `~/.pm/config.json`
- Database backup functionality

#### Phase 2: Goals & Todos
- Goal CRUD operations: `pm goal add/list/show/update`
- Todo CRUD operations: `pm todo add/list/show/start/complete/block`
- Multi-factor priority scoring algorithm (7 weighted factors)
- Priority management: `pm prioritize` command
- Filtering and sorting for goals and todos
- Status workflow: open → in_progress → completed (or blocked)
- Effort estimation (S/M/L/XL) with quick-win scoring
- Deadline tracking with urgency calculation
- Blocking relationships between todos
- `pm todos --next` for top 5 priorities
- `pm todos --blocked` for blocked items

#### Phase 3: Git Integration
- GitPython-based commit scanning
- `pm sync` command for fetching commits (single project or --all)
- Commit message parsing for todo references (#T42, #42, fixes #42, etc.)
- Auto-linking commits to todos (bidirectional)
- Auto-completion of todos when commit has completion keywords
- Activity metrics calculation (insertions, deletions, files changed)
- `pm activity` command with timeline visualization
- `pm commits` command with filtering by author and date
- Project last_activity_at tracking
- `pm sync-and-prioritize` workflow command
- 6 regex patterns for todo references in commit messages

#### Phase 4: Analytics & Dashboards
- Comprehensive metrics calculator (MetricsCalculator class)
- `pm metrics` dashboard with Rich visualizations
- Health score calculation (0-100 with 5 status labels)
- Velocity tracking (todos completed per day)
- Completion rate calculation
- Velocity trend analysis (4-week rolling average)
- Burn-down tracking for goals
- Todo/goal breakdown by status
- Overdue and upcoming deadline tracking
- `pm review` command (daily standup helper with top priorities)
- Report generation: `pm report` (markdown and HTML formats)
- Detailed metrics view with trends

#### Phase 5: Advanced Features
- CLAUDE.md parsing (ClaudeMdParser class)
- Automatic extraction of project descriptions, tech stack, commands, goals, architecture
- `pm import-claude-md` command with --auto-import flag
- Intelligent category inference (feature/bugfix/refactor/docs/ops)
- Priority suggestion based on keywords
- Interactive workflows with questionary:
  - `pm start`: Pick project → pick todo → start working
  - `pm plan`: Interactive goal planning wizard
  - `pm standup`: Daily standup workflow
- Export/import system (ExportImport class):
  - `pm export` command: export project to JSON
  - `pm backup` command: backup all projects to JSON files
- JSON export format v1.0 with full data preservation
- Support for multiple goal section types (Next Steps, TODO, Roadmap, Planned Features)

#### Phase 6: Polish & Distribution
- GitHub Actions CI/CD workflow (test, lint, build)
- Multi-OS testing (Ubuntu, macOS)
- Multi-Python version testing (3.10, 3.11, 3.12)
- MIT License
- Shell completion scripts (bash and zsh)
- Comprehensive CHANGELOG
- Tutorial documentation
- Contributing guidelines
- Code formatting with black and ruff
- Package building and PyPI preparation

### Technical Details

- **Python**: 3.10+ required
- **Dependencies**: Click, SQLAlchemy, Rich, GitPython, Questionary, Pydantic, python-dateutil
- **Database**: SQLite with foreign key constraints and cascade deletes
- **Test Coverage**: 56 tests across 6 test suites (28% overall, 78-97% for core modules)
- **Code Size**: ~3,500+ lines across 8 Python modules

### Fixed

- SQLAlchemy reserved name conflict (`metadata` → `extra_data`)
- DetachedInstanceError in session management
- Missing `timedelta` import in cli.py
- Test expectation for category inference ("error" keyword → bugfix)
- Deprecation warnings for `datetime.utcnow()` usage

[0.1.0]: https://github.com/yourusername/pm-cli/releases/tag/v0.1.0
