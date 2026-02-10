"""Tests for metrics and analytics"""

import pytest
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pm.models import Base, Project, Goal, Todo, Commit
from pm.metrics import MetricsCalculator


@pytest.fixture
def db_session():
    """Create an in-memory database for testing"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_project(db_session):
    """Create a sample project"""
    project = Project(
        name="TestProject",
        path="/test/path",
        priority=70,
        has_git=True,
        last_activity_at=datetime.utcnow(),
    )
    db_session.add(project)
    db_session.commit()
    return project


@pytest.fixture
def calculator():
    """Create a MetricsCalculator instance"""
    return MetricsCalculator()


def test_calculate_velocity_no_todos(calculator, sample_project, db_session):
    """Test velocity calculation with no completed todos"""
    velocity = calculator.calculate_velocity(sample_project, db_session, days=7)
    assert velocity == 0.0


def test_calculate_velocity_with_completed_todos(calculator, sample_project, db_session):
    """Test velocity calculation with completed todos"""
    # Add completed todos in last 7 days
    for i in range(3):
        todo = Todo(
            project_id=sample_project.id,
            title=f"Todo {i}",
            status="completed",
            completed_at=datetime.utcnow() - timedelta(days=i),
        )
        db_session.add(todo)

    db_session.commit()

    velocity = calculator.calculate_velocity(sample_project, db_session, days=7)
    assert velocity == 3 / 7  # 3 todos in 7 days


def test_calculate_completion_rate_empty(calculator, sample_project, db_session):
    """Test completion rate with no todos"""
    rate = calculator.calculate_completion_rate(sample_project, db_session)
    assert rate == 0.0


def test_calculate_completion_rate_with_todos(calculator, sample_project, db_session):
    """Test completion rate calculation"""
    # Add 10 todos, 6 completed
    for i in range(10):
        status = "completed" if i < 6 else "open"
        todo = Todo(project_id=sample_project.id, title=f"Todo {i}", status=status)
        db_session.add(todo)

    db_session.commit()

    rate = calculator.calculate_completion_rate(sample_project, db_session)
    assert rate == 60.0  # 6/10 = 60%


def test_calculate_health_score(calculator, sample_project, db_session):
    """Test health score calculation"""
    # Add recent activity
    commit = Commit(
        project_id=sample_project.id,
        sha="abc123",
        message="Test commit",
        author="Test <test@example.com>",
        committed_at=datetime.utcnow() - timedelta(days=2),
        insertions=100,
        deletions=50,
        files_changed=5,
    )
    db_session.add(commit)

    # Add completed todos
    for i in range(5):
        todo = Todo(
            project_id=sample_project.id,
            title=f"Todo {i}",
            status="completed",
            completed_at=datetime.utcnow() - timedelta(days=i),
        )
        db_session.add(todo)

    db_session.commit()

    score, status = calculator.calculate_health_score(sample_project, db_session)

    assert 0 <= score <= 100
    assert status in ["Excellent", "Good", "Fair", "Needs Attention", "Critical"]
    assert score > 0  # Should have some score with activity


def test_get_todo_breakdown(calculator, sample_project, db_session):
    """Test todo status breakdown"""
    # Add todos with different statuses
    statuses = ["open", "open", "in_progress", "completed", "completed", "completed", "blocked"]

    for status in statuses:
        todo = Todo(project_id=sample_project.id, title=f"Todo {status}", status=status)
        db_session.add(todo)

    db_session.commit()

    breakdown = calculator.get_todo_breakdown(sample_project, db_session)

    assert breakdown["open"] == 2
    assert breakdown["in_progress"] == 1
    assert breakdown["completed"] == 3
    assert breakdown["blocked"] == 1


def test_get_goal_breakdown(calculator, sample_project, db_session):
    """Test goal status breakdown"""
    # Add goals with different statuses
    statuses = ["active", "active", "completed", "cancelled"]

    for status in statuses:
        goal = Goal(
            project_id=sample_project.id,
            title=f"Goal {status}",
            category="feature",
            priority=50,
            status=status,
        )
        db_session.add(goal)

    db_session.commit()

    breakdown = calculator.get_goal_breakdown(sample_project, db_session)

    assert breakdown["active"] == 2
    assert breakdown["completed"] == 1
    assert breakdown["cancelled"] == 1


def test_get_overdue_todos(calculator, sample_project, db_session):
    """Test getting overdue todos"""
    today = date.today()

    # Add overdue todo
    overdue_todo = Todo(
        project_id=sample_project.id,
        title="Overdue",
        status="open",
        due_date=today - timedelta(days=5),
    )

    # Add future todo
    future_todo = Todo(
        project_id=sample_project.id,
        title="Future",
        status="open",
        due_date=today + timedelta(days=5),
    )

    db_session.add_all([overdue_todo, future_todo])
    db_session.commit()

    overdue = calculator.get_overdue_todos(sample_project, db_session)

    assert len(overdue) == 1
    assert overdue[0].title == "Overdue"


def test_get_upcoming_deadlines(calculator, sample_project, db_session):
    """Test getting upcoming deadlines"""
    today = date.today()

    # Add todos with different deadlines
    upcoming = Todo(
        project_id=sample_project.id,
        title="Upcoming",
        status="open",
        due_date=today + timedelta(days=3),
    )

    far_future = Todo(
        project_id=sample_project.id,
        title="Far Future",
        status="open",
        due_date=today + timedelta(days=30),
    )

    db_session.add_all([upcoming, far_future])
    db_session.commit()

    upcoming_todos = calculator.get_upcoming_deadlines(sample_project, db_session, days=7)

    assert len(upcoming_todos) == 1
    assert upcoming_todos[0].title == "Upcoming"


def test_get_velocity_trend(calculator, sample_project, db_session):
    """Test velocity trend calculation"""
    # Add todos completed over different weeks
    for i in range(4):
        for j in range(2):  # 2 todos per week
            todo = Todo(
                project_id=sample_project.id,
                title=f"Todo week {i} - {j}",
                status="completed",
                completed_at=datetime.utcnow() - timedelta(days=i * 7 + j),
            )
            db_session.add(todo)

    db_session.commit()

    trend = calculator.get_velocity_trend(sample_project, db_session, weeks=4)

    assert len(trend) == 4
    for week_data in trend:
        assert "week_start" in week_data
        assert "week_end" in week_data
        assert "velocity" in week_data
        assert "todos_completed" in week_data


def test_calculate_burn_down(calculator, sample_project, db_session):
    """Test burn-down calculation for a goal"""
    goal = Goal(
        project_id=sample_project.id,
        title="Test Goal",
        category="feature",
        priority=80,
        target_date=date.today() + timedelta(days=30),
    )
    db_session.add(goal)
    db_session.flush()

    # Add todos (5 total, 3 completed)
    for i in range(5):
        status = "completed" if i < 3 else "open"
        todo = Todo(project_id=sample_project.id, goal_id=goal.id, title=f"Todo {i}", status=status)
        db_session.add(todo)

    db_session.commit()

    burn_down = calculator.calculate_burn_down(goal, db_session)

    assert burn_down["total_todos"] == 5
    assert burn_down["completed_todos"] == 3
    assert burn_down["remaining_todos"] == 2
    assert burn_down["progress"] == 60.0
    assert burn_down["days_remaining"] == 30


def test_health_score_with_overdue_todos(calculator, sample_project, db_session):
    """Test that overdue todos negatively affect health score"""
    # Create two scenarios: one with overdue, one without
    project_no_overdue = Project(
        name="NoOverdue", path="/test/path2", has_git=True, last_activity_at=datetime.utcnow()
    )
    db_session.add(project_no_overdue)
    db_session.commit()

    # Add overdue todo to sample_project
    overdue_todo = Todo(
        project_id=sample_project.id,
        title="Overdue",
        status="open",
        due_date=date.today() - timedelta(days=5),
    )
    db_session.add(overdue_todo)

    # Add on-time todo to project_no_overdue
    ontime_todo = Todo(
        project_id=project_no_overdue.id,
        title="On Time",
        status="open",
        due_date=date.today() + timedelta(days=5),
    )
    db_session.add(ontime_todo)
    db_session.commit()

    score_with_overdue, _ = calculator.calculate_health_score(sample_project, db_session)
    score_without_overdue, _ = calculator.calculate_health_score(project_no_overdue, db_session)

    # Project without overdue should score higher (assuming similar other factors)
    assert score_without_overdue > score_with_overdue


def test_health_score_with_blocked_todos(calculator, sample_project, db_session):
    """Test that blocked todos negatively affect health score"""
    # Add blocked todo
    blocked_todo = Todo(
        project_id=sample_project.id,
        title="Blocked",
        status="blocked",
        blocked_by={"todo_ids": [999]},
    )
    db_session.add(blocked_todo)
    db_session.commit()

    score, _ = calculator.calculate_health_score(sample_project, db_session)

    # Score should be reduced due to blocked todo
    assert score < 100
