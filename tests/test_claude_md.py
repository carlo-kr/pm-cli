"""Tests for CLAUDE.md parsing"""

import pytest
from pathlib import Path
from pm.claude_md import ClaudeMdParser, ExportImport


@pytest.fixture
def parser():
    """Create a ClaudeMdParser instance"""
    return ClaudeMdParser()


@pytest.fixture
def sample_claude_md(tmp_path):
    """Create a sample CLAUDE.md file"""
    content = """# Test Project

## Overview

This is a test project for parsing CLAUDE.md files. It uses Python and TypeScript
to build amazing features.

## Commands

```bash
# Install dependencies
npm install

# Run tests
pytest tests/

# Start server
python manage.py runserver
```

## Architecture

The project follows a clean architecture pattern with three main layers:
- Presentation
- Business Logic
- Data Access

## Next Steps

- [ ] Implement user authentication
- [x] Add database migrations
- Fix the critical security bug in login
- Improve performance of API endpoints
- Write documentation for API

## TODO

1. Refactor the authentication module
2. Add unit tests for user service
3. Deploy to production

## Tech Stack

- Python 3.10+
- TypeScript
- React
- PostgreSQL
- Docker
"""

    file_path = tmp_path / "CLAUDE.md"
    file_path.write_text(content)
    return file_path


def test_extract_description(parser, sample_claude_md):
    """Test extracting project description"""
    data = parser.parse_file(sample_claude_md)

    assert data['description'] is not None
    assert 'test project' in data['description'].lower()
    assert len(data['description']) <= 500


def test_extract_tech_stack(parser, sample_claude_md):
    """Test extracting technology stack"""
    data = parser.parse_file(sample_claude_md)

    tech_stack = data['tech_stack']
    assert 'Python' in tech_stack
    assert 'Typescript' in tech_stack
    assert 'React' in tech_stack
    assert 'Postgresql' in tech_stack
    assert 'Docker' in tech_stack


def test_extract_commands(parser, sample_claude_md):
    """Test extracting commands from Commands section"""
    data = parser.parse_file(sample_claude_md)

    commands = data['commands']
    assert len(commands) > 0

    # Check that some expected commands are present
    command_values = ' '.join(commands.values())
    assert 'npm install' in command_values or 'pytest' in command_values


def test_extract_goals(parser, sample_claude_md):
    """Test extracting goals from Next Steps and TODO"""
    data = parser.parse_file(sample_claude_md)

    goals = data['goals']
    assert len(goals) > 0

    # Check specific goals
    titles = [g['title'] for g in goals]
    assert any('authentication' in t.lower() for t in titles)
    assert any('security' in t.lower() or 'bug' in t.lower() for t in titles)
    assert any('refactor' in t.lower() for t in titles)


def test_infer_category(parser):
    """Test category inference from goal titles"""
    assert parser._infer_category("Fix authentication bug") == "bugfix"
    assert parser._infer_category("Add new feature") == "feature"
    assert parser._infer_category("Refactor user service") == "refactor"
    assert parser._infer_category("Write API documentation") == "docs"
    assert parser._infer_category("Deploy to production") == "ops"
    assert parser._infer_category("Improve code structure") == "refactor"


def test_suggest_priority(parser):
    """Test priority suggestion from goal titles"""
    assert parser.suggest_priority("Critical security fix") == 90
    assert parser.suggest_priority("Urgent: production down") == 90
    assert parser.suggest_priority("Fix important bug") == 70
    assert parser.suggest_priority("Improve performance") == 60
    assert parser.suggest_priority("Add new dashboard") == 50


def test_parse_checkbox_items(parser):
    """Test parsing checkbox list items"""
    content = """
- [ ] Implement feature A
- [x] Complete feature B
- [ ] Fix bug C
"""
    goals = parser._parse_goal_items(content)

    assert len(goals) == 3
    assert goals[0]['title'] == "Implement feature A"
    assert goals[1]['title'] == "Complete feature B"
    assert goals[2]['title'] == "Fix bug C"


def test_parse_bullet_items(parser):
    """Test parsing bullet list items"""
    content = """
- Add user management
- Implement notifications
- Create admin panel
"""
    goals = parser._parse_goal_items(content)

    assert len(goals) == 3
    assert goals[0]['title'] == "Add user management"


def test_parse_numbered_items(parser):
    """Test parsing numbered list items"""
    content = """
1. Set up CI/CD pipeline
2. Configure monitoring
3. Add logging
"""
    goals = parser._parse_goal_items(content)

    assert len(goals) == 3
    assert goals[0]['title'] == "Set up CI/CD pipeline"


def test_extract_architecture(parser, sample_claude_md):
    """Test extracting architecture description"""
    data = parser.parse_file(sample_claude_md)

    architecture = data['architecture']
    assert architecture is not None
    assert 'clean architecture' in architecture.lower()
    assert len(architecture) <= 1000


def test_parse_file_missing(parser, tmp_path):
    """Test parsing non-existent file"""
    missing_file = tmp_path / "missing.md"
    data = parser.parse_file(missing_file)

    assert data == {}


def test_export_project_structure():
    """Test export data structure"""
    exporter = ExportImport()

    # Create mock objects with minimal attributes
    class MockProject:
        name = "Test"
        path = "/test"
        description = "Test project"
        tech_stack = ["Python"]
        status = "active"
        priority = 50
        has_git = True
        extra_data = {}

    class MockGoal:
        title = "Test Goal"
        description = "Test"
        category = "feature"
        priority = 80
        status = "active"
        target_date = None

    class MockTodo:
        title = "Test Todo"
        description = "Test"
        goal = None
        status = "open"
        effort_estimate = "M"
        due_date = None
        tags = {}
        blocked_by = {}

    project = MockProject()
    goals = [MockGoal()]
    todos = [MockTodo()]
    commits = []

    data = exporter.export_project(project, goals, todos, commits, None)

    assert 'version' in data
    assert 'project' in data
    assert 'goals' in data
    assert 'todos' in data
    assert 'commits' in data

    assert data['project']['name'] == "Test"
    assert len(data['goals']) == 1
    assert len(data['todos']) == 1


def test_import_project_validation():
    """Test import data validation"""
    exporter = ExportImport()

    # Valid data
    valid_data = {
        'version': '1.0',
        'project': {},
        'goals': [],
        'todos': [],
    }

    success, message = exporter.import_project(valid_data, None)
    assert success is True

    # Invalid data - missing key
    invalid_data = {
        'version': '1.0',
        'project': {},
    }

    success, message = exporter.import_project(invalid_data, None)
    assert success is False
    assert 'Missing required key' in message


def test_parse_multiple_next_steps_sections(parser, tmp_path):
    """Test parsing when multiple goal sections exist"""
    content = """# Project

## Next Steps
- Feature A
- Feature B

## Roadmap
- Feature C
- Feature D

## TODO
- Fix bug E
"""

    file_path = tmp_path / "CLAUDE.md"
    file_path.write_text(content)

    data = parser.parse_file(file_path)
    goals = data['goals']

    # Should find goals from all three sections
    assert len(goals) >= 5
    titles = [g['title'] for g in goals]
    assert "Feature A" in titles
    assert "Feature C" in titles
    assert "Fix bug E" in titles
