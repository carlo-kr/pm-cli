# Contributing to PM CLI

Thank you for your interest in contributing to PM CLI! This document provides guidelines and instructions for contributing.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Development Workflow](#development-workflow)
5. [Testing](#testing)
6. [Code Style](#code-style)
7. [Commit Messages](#commit-messages)
8. [Pull Request Process](#pull-request-process)
9. [Project Structure](#project-structure)

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inspiring community for all. Please be respectful and constructive in all interactions.

### Our Standards

- Use welcoming and inclusive language
- Be respectful of differing viewpoints and experiences
- Gracefully accept constructive criticism
- Focus on what is best for the community
- Show empathy towards other community members

## Getting Started

### Ways to Contribute

- **Report bugs**: Found a bug? [Open an issue](https://github.com/yourusername/pm-cli/issues/new)
- **Suggest features**: Have an idea? [Start a discussion](https://github.com/yourusername/pm-cli/discussions)
- **Fix bugs**: Check out [issues labeled "bug"](https://github.com/yourusername/pm-cli/labels/bug)
- **Add features**: Check out [issues labeled "enhancement"](https://github.com/yourusername/pm-cli/labels/enhancement)
- **Improve docs**: Documentation improvements are always welcome
- **Write tests**: Help us improve test coverage

## Development Setup

### Prerequisites

- Python 3.10 or higher
- Git
- pip (Python package manager)

### Setup Steps

1. **Fork the repository**
   ```bash
   # Click "Fork" on GitHub, then clone your fork
   git clone https://github.com/YOUR_USERNAME/pm-cli.git
   cd pm-cli
   ```

2. **Add upstream remote**
   ```bash
   git remote add upstream https://github.com/yourusername/pm-cli.git
   ```

3. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. **Install in development mode**
   ```bash
   pip install -e ".[dev]"
   ```

5. **Verify installation**
   ```bash
   pm --version
   pytest tests/ -v
   ```

## Development Workflow

### 1. Create a Branch

Always create a new branch for your work:

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

**Branch naming conventions:**
- `feature/description` - For new features
- `fix/description` - For bug fixes
- `docs/description` - For documentation
- `test/description` - For test improvements
- `refactor/description` - For code refactoring

### 2. Make Changes

- Write clear, readable code
- Add docstrings to functions and classes
- Update tests as needed
- Update documentation if changing behavior

### 3. Test Your Changes

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_priority.py -v

# Run with coverage
pytest tests/ --cov=pm --cov-report=term-missing

# Run specific test
pytest tests/test_priority.py::test_effort_value_scoring -v
```

### 4. Format Your Code

```bash
# Format with black
black src/ tests/

# Lint with ruff
ruff check src/ tests/

# Fix auto-fixable issues
ruff check --fix src/ tests/
```

### 5. Commit Your Changes

See [Commit Messages](#commit-messages) section below.

### 6. Push to Your Fork

```bash
git push origin feature/your-feature-name
```

### 7. Open a Pull Request

Go to GitHub and open a pull request from your branch to `main`.

## Testing

### Running Tests

```bash
# All tests
pytest tests/

# Specific module
pytest tests/test_priority.py

# With verbose output
pytest tests/ -v

# With coverage report
pytest tests/ --cov=pm --cov-report=html
# Open htmlcov/index.html to view coverage
```

### Writing Tests

We use pytest for testing. Tests should:

1. **Be isolated**: Each test should be independent
2. **Use fixtures**: Use pytest fixtures for setup/teardown
3. **Be descriptive**: Test names should describe what they test
4. **Cover edge cases**: Test boundary conditions and error cases

**Example test structure:**

```python
import pytest
from pm.priority import PriorityCalculator

@pytest.fixture
def calculator():
    """Create a PriorityCalculator instance"""
    return PriorityCalculator()

@pytest.fixture
def sample_todo(db_session):
    """Create a sample todo for testing"""
    project = Project(name="Test", path="/test")
    db_session.add(project)

    todo = Todo(
        title="Test Todo",
        project=project,
        effort_estimate="M",
        status="open"
    )
    db_session.add(todo)
    db_session.commit()
    return todo

def test_effort_value_scoring(calculator, sample_todo):
    """Test that effort size affects priority correctly"""
    # Small effort should score higher
    sample_todo.effort_estimate = "S"
    score = calculator._effort_value_score(sample_todo)
    assert score == 80

    # XL effort should score lower
    sample_todo.effort_estimate = "XL"
    score = calculator._effort_value_score(sample_todo)
    assert score == 20
```

### Test Coverage Goals

- **Core modules**: Aim for >80% coverage
- **New features**: All new code should include tests
- **Bug fixes**: Add regression tests

Current coverage by module:
- `models.py`: 94%
- `claude_md.py`: 97%
- `priority.py`: 78%
- `metrics.py`: 78%
- `utils.py`: 69%
- `git_integration.py`: 41% (needs improvement)

## Code Style

We follow PEP 8 with some modifications:

### Formatting

- **Line length**: 100 characters (configured in pyproject.toml)
- **Formatter**: black (run with `black src/ tests/`)
- **Linter**: ruff (run with `ruff check src/ tests/`)

### Naming Conventions

```python
# Variables and functions: snake_case
def calculate_priority(todo_id):
    priority_score = 0

# Classes: PascalCase
class PriorityCalculator:
    pass

# Constants: UPPER_SNAKE_CASE
MAX_PRIORITY = 100
DEFAULT_WORKSPACE = "~/Building/Experiments"

# Private methods: leading underscore
def _internal_helper(self):
    pass
```

### Docstrings

Use Google-style docstrings:

```python
def calculate_priority(self, todo: Todo, session: Session) -> float:
    """Calculate priority score for a todo using multi-factor algorithm.

    The priority score is calculated as a weighted sum of 7 factors:
    goal priority, project priority, age urgency, deadline pressure,
    effort value, git activity, and blocking impact.

    Args:
        todo: The todo object to calculate priority for
        session: Active database session

    Returns:
        Priority score between 0.0 and 100.0

    Raises:
        ValueError: If todo has invalid effort_estimate
    """
    pass
```

### Type Hints

Use type hints for function signatures:

```python
from typing import Optional, List, Dict

def get_todos(
    project_id: Optional[int] = None,
    status: str = "open"
) -> List[Todo]:
    """Get todos with optional filtering"""
    pass
```

### Imports

Organize imports in this order:

```python
# Standard library
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Third-party
import click
from rich.console import Console
from sqlalchemy import select
from sqlalchemy.orm import Session

# Local
from pm.db import get_db_manager
from pm.models import Project, Todo, Goal
from pm.utils import format_date
```

## Commit Messages

### Format

We follow the Conventional Commits specification:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Adding or updating tests
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `style`: Code style changes (formatting, etc.)
- `chore`: Maintenance tasks
- `ci`: CI/CD changes

### Examples

**Feature:**
```
feat(cli): add interactive todo picker command

Add `pm pick` command that presents an interactive menu
of top-priority todos for quick selection and starting.

Uses questionary for the interactive interface.
```

**Bug fix:**
```
fix(priority): correct deadline pressure calculation for overdue todos

Overdue todos were not receiving maximum deadline pressure score.
Changed calculation to return 100.0 for any negative days_until_due.

Fixes #42
```

**Documentation:**
```
docs: add tutorial section on git integration

Added comprehensive examples of commit message patterns
and how to link commits to todos automatically.
```

### Best Practices

- **Subject line**: Imperative mood ("add feature" not "added feature")
- **Length**: Subject ≤ 50 chars, body lines ≤ 72 chars
- **Reference issues**: Include "Fixes #123" or "Closes #456"
- **Explain why**: Body should explain why the change was needed

## Pull Request Process

### Before Submitting

1. ✅ Tests pass: `pytest tests/`
2. ✅ Code is formatted: `black src/ tests/`
3. ✅ No lint errors: `ruff check src/ tests/`
4. ✅ Documentation updated (if needed)
5. ✅ CHANGELOG.md updated (for significant changes)

### PR Description Template

```markdown
## Description
Brief description of what this PR does.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
Describe the tests you ran and how to reproduce them.

## Checklist
- [ ] My code follows the code style of this project
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] I have updated the documentation accordingly
- [ ] All tests pass locally
```

### Review Process

1. **Automated checks**: CI will run tests and linting
2. **Code review**: Maintainers will review your code
3. **Feedback**: Address any feedback or requested changes
4. **Approval**: Once approved, a maintainer will merge

### After Merge

1. Delete your branch (GitHub offers this automatically)
2. Update your local repository:
   ```bash
   git checkout main
   git pull upstream main
   ```
3. Celebrate! 🎉

## Project Structure

Understanding the codebase structure:

```
pm-cli/
├── .github/
│   ├── workflows/
│   │   └── ci.yml              # CI/CD configuration
│   └── CONTRIBUTING.md         # This file
├── completions/
│   ├── pm-completion.bash      # Bash completion script
│   └── pm-completion.zsh       # Zsh completion script
├── src/
│   └── pm/
│       ├── __init__.py         # Package initialization
│       ├── cli.py              # Main CLI application (Click commands)
│       ├── models.py           # SQLAlchemy ORM models
│       ├── db.py               # Database manager
│       ├── priority.py         # Priority calculation algorithm
│       ├── metrics.py          # Analytics and metrics
│       ├── git_integration.py  # Git commit scanning
│       ├── claude_md.py        # CLAUDE.md parsing and export/import
│       └── utils.py            # Helper functions
├── tests/
│   ├── test_models.py          # Model tests
│   ├── test_priority.py        # Priority algorithm tests
│   ├── test_metrics.py         # Metrics tests
│   ├── test_git_integration.py # Git integration tests
│   ├── test_claude_md.py       # CLAUDE.md parser tests
│   └── test_utils.py           # Utility function tests
├── pyproject.toml              # Package configuration
├── setup.py                    # Setup configuration
├── README.md                   # User documentation
├── TUTORIAL.md                 # Comprehensive tutorial
├── CHANGELOG.md                # Version history
└── LICENSE                     # MIT License
```

### Key Modules

**cli.py** (1100+ lines)
- All Click commands and CLI interface
- Command groups: projects, goals, todos, git, metrics, interactive
- Rich output formatting

**models.py** (180 lines)
- SQLAlchemy ORM models: Project, Goal, Todo, Commit, Metric, ActivityLog
- Relationships and constraints

**priority.py** (215 lines)
- PriorityCalculator class
- Multi-factor weighted scoring algorithm
- 7 scoring factors with adjustments

**metrics.py** (360 lines)
- MetricsCalculator class
- Health score, velocity, completion rate
- Trend analysis and burn-down tracking

**git_integration.py** (247 lines)
- GitScanner class
- Commit message parsing (6 regex patterns)
- Auto-completion detection

**claude_md.py** (372 lines)
- ClaudeMdParser class for CLAUDE.md files
- ExportImport class for backup/restore
- Regex-based markdown parsing

## Questions?

- **General questions**: [Start a discussion](https://github.com/yourusername/pm-cli/discussions)
- **Bug reports**: [Open an issue](https://github.com/yourusername/pm-cli/issues)
- **Security issues**: Email security@example.com (do not open public issue)

## Recognition

Contributors will be recognized in:
- GitHub Contributors page
- CHANGELOG.md (for significant contributions)
- Project README.md

Thank you for contributing to PM CLI! 🚀
