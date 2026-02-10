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

### Basic Installation

```bash
cd ~/Building/Experiments/pm
pip install -e .
```

After installation, the `pm` command will be available globally.

### Shell Completion (Optional)

**Bash:**
```bash
# Copy completion script
sudo cp completions/pm-completion.bash /etc/bash_completion.d/

# Or source in ~/.bashrc
echo "source $(pwd)/completions/pm-completion.bash" >> ~/.bashrc
source ~/.bashrc
```

**Zsh:**
```bash
# Copy to zsh completions directory
sudo cp completions/pm-completion.zsh /usr/local/share/zsh/site-functions/_pm

# Reload completions
rm -f ~/.zcompdump; compinit
```

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

### Git Integration

```bash
pm sync PROJECT                       # Sync git commits to database
pm sync --all                         # Sync all projects
pm commits PROJECT                    # Show recent commits
pm commits PROJECT --author "Name"    # Filter by author
pm commits PROJECT --since 2026-02-01 # Filter by date
pm activity PROJECT                   # Show activity timeline
pm activity PROJECT --days 7          # Last 7 days
pm sync-and-prioritize                # Sync and recalc (daily workflow)
```

**Commit Linking:**
Reference todos in commit messages to auto-link:
- `#T42` or `#42` - Links commit to todo
- `fixes #42`, `closes #42`, `resolves #42`, `completes #42` - Links and auto-completes todo

### Analytics & Dashboards

```bash
pm metrics PROJECT                    # Show metrics dashboard
pm metrics PROJECT --detailed         # Include velocity trends
pm review                             # Daily standup review
pm review --project PROJECT           # Focus on specific project
pm report PROJECT --format markdown   # Generate markdown report
pm report PROJECT --format html --output report.html
```

**Metrics Tracked:**
- Health score (0-100) with status labels
- Velocity (todos/day) over time
- Completion rate percentage
- Todo/goal breakdowns by status
- Overdue and upcoming deadlines
- 4-week velocity trends

### CLAUDE.md Integration

```bash
pm import-claude-md PROJECT           # Import goals from CLAUDE.md
pm import-claude-md PROJECT --auto-import  # Auto-import without confirmation
```

**What gets imported:**
- Goals from Next Steps, TODO, Roadmap, Planned Features sections
- Categories automatically inferred (feature/bugfix/refactor/docs/ops)
- Priorities suggested based on keywords (critical, urgent, important)

### Interactive Workflows

```bash
pm start                              # Pick project → pick todo → start
pm plan PROJECT                       # Interactive goal planning wizard
pm standup                            # Daily standup workflow
```

### Export & Backup

```bash
pm export PROJECT --output FILE       # Export project to JSON
pm backup                             # Backup all projects
pm backup --output DIR                # Custom backup directory
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

**Phase 3 (Complete):**
- ✅ Git commit scanning with GitPython
- ✅ Automatic commit-todo linking (#T42, fixes #42, etc.)
- ✅ Auto-completion of todos from commit keywords
- ✅ Activity timeline visualization
- ✅ Commit statistics and metrics
- ✅ Project activity tracking
- ✅ 29 passing tests (13 new git integration tests)

**Phase 4 (Complete):**
- ✅ Comprehensive metrics calculator
- ✅ Health score tracking (multi-factor 0-100 scale)
- ✅ Velocity tracking and trend analysis
- ✅ Daily standup review workflow
- ✅ Report generation (markdown/HTML)
- ✅ Burn-down tracking for goals
- ✅ 42 passing tests (13 new metrics tests)

**Phase 5 (Complete):**
- ✅ CLAUDE.md parsing and automatic import
- ✅ Interactive workflows (pm start, pm plan, pm standup)
- ✅ Export/import for backup (JSON format)
- ✅ Intelligent category inference and priority suggestion
- ✅ 56 passing tests (14 new CLAUDE.md tests)

**Phase 6 (Complete):**
- ✅ GitHub Actions CI/CD (test, lint, build)
- ✅ Multi-OS and multi-Python version testing
- ✅ Shell completion scripts (bash and zsh)
- ✅ Comprehensive tutorial documentation
- ✅ Contributing guidelines
- ✅ MIT License
- ✅ Package ready for distribution

## Tech Stack

- **Python 3.10+**
- **Click** - CLI framework
- **SQLAlchemy** - ORM and database
- **Rich** - Beautiful terminal output
- **GitPython** - Git integration
- **Pydantic** - Data validation
- **Questionary** - Interactive prompts

## Documentation

- **[Tutorial](TUTORIAL.md)** - Comprehensive guide with examples
- **[Contributing](.github/CONTRIBUTING.md)** - Contribution guidelines
- **[Changelog](CHANGELOG.md)** - Version history

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](.github/CONTRIBUTING.md) for:
- Development setup
- Code style guidelines
- Testing requirements
- Pull request process

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/pm-cli/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/pm-cli/discussions)
- **Tutorial**: See [TUTORIAL.md](TUTORIAL.md) for detailed usage examples

## License

MIT - See [LICENSE](LICENSE) for details
