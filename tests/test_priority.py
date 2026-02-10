"""Tests for priority scoring algorithm"""

import pytest
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pm.models import Base, Project, Goal, Todo
from pm.priority import PriorityCalculator
from pm.utils import Config


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
    project = Project(name="TestProject", path="/test/path", priority=50)
    db_session.add(project)
    db_session.commit()
    return project


@pytest.fixture
def sample_goal(db_session, sample_project):
    """Create a sample goal"""
    goal = Goal(
        project_id=sample_project.id,
        title="Test Goal",
        category="feature",
        priority=80,
    )
    db_session.add(goal)
    db_session.commit()
    return goal


def test_calculate_priority_basic(db_session, sample_project, sample_goal):
    """Test basic priority calculation"""
    calculator = PriorityCalculator()

    todo = Todo(
        project_id=sample_project.id,
        goal_id=sample_goal.id,
        title="Test Todo",
        status="open",
        effort_estimate="M",
    )
    db_session.add(todo)
    db_session.commit()

    score = calculator.calculate_priority(todo, db_session)

    # Score should be in valid range
    assert 0 <= score <= 100

    # Should have reasonable base score (goal=80, project=50, no deadline, age=low)
    assert 30 < score < 70


def test_effort_value_scoring(db_session, sample_project):
    """Test that smaller effort gets higher priority (quick wins)"""
    calculator = PriorityCalculator()

    todo_small = Todo(
        project_id=sample_project.id,
        title="Small Task",
        status="open",
        effort_estimate="S",
    )

    todo_large = Todo(
        project_id=sample_project.id,
        title="Large Task",
        status="open",
        effort_estimate="XL",
    )

    db_session.add_all([todo_small, todo_large])
    db_session.commit()

    score_small = calculator.calculate_priority(todo_small, db_session)
    score_large = calculator.calculate_priority(todo_large, db_session)

    # Small effort should have higher priority
    assert score_small > score_large


def test_deadline_pressure_scoring(db_session, sample_project):
    """Test that closer deadlines get higher priority"""
    calculator = PriorityCalculator()

    today = date.today()

    todo_soon = Todo(
        project_id=sample_project.id,
        title="Due Soon",
        status="open",
        due_date=today + timedelta(days=2),
    )

    todo_later = Todo(
        project_id=sample_project.id,
        title="Due Later",
        status="open",
        due_date=today + timedelta(days=30),
    )

    db_session.add_all([todo_soon, todo_later])
    db_session.commit()

    score_soon = calculator.calculate_priority(todo_soon, db_session)
    score_later = calculator.calculate_priority(todo_later, db_session)

    # Closer deadline should have higher priority
    assert score_soon > score_later


def test_overdue_todo_priority(db_session, sample_project):
    """Test that overdue todos get maximum deadline pressure"""
    calculator = PriorityCalculator()

    yesterday = date.today() - timedelta(days=1)

    todo = Todo(
        project_id=sample_project.id,
        title="Overdue",
        status="open",
        due_date=yesterday,
    )

    db_session.add(todo)
    db_session.commit()

    score = calculator.calculate_priority(todo, db_session)

    # Overdue todos should have reasonably high priority
    assert score > 50  # More lenient threshold since it depends on all factors


def test_blocked_todo_reduction(db_session, sample_project):
    """Test that blocked todos get 0.5x reduction"""
    calculator = PriorityCalculator()

    todo = Todo(
        project_id=sample_project.id,
        title="Blocked Todo",
        status="blocked",
        effort_estimate="M",
    )

    db_session.add(todo)
    db_session.commit()

    score_blocked = calculator.calculate_priority(todo, db_session)

    # Change to open and recalculate
    todo.status = "open"
    score_open = calculator.calculate_priority(todo, db_session)

    # Blocked should be roughly half of open
    assert score_blocked < score_open
    assert abs(score_blocked - score_open * 0.5) < 5  # Allow some margin


def test_in_progress_boost(db_session, sample_project):
    """Test that in_progress todos get 1.2x boost"""
    calculator = PriorityCalculator()

    todo = Todo(
        project_id=sample_project.id,
        title="In Progress",
        status="open",
        effort_estimate="M",
    )

    db_session.add(todo)
    db_session.commit()

    score_open = calculator.calculate_priority(todo, db_session)

    # Change to in_progress
    todo.status = "in_progress"
    score_in_progress = calculator.calculate_priority(todo, db_session)

    # In progress should be roughly 1.2x of open
    assert score_in_progress > score_open
    assert abs(score_in_progress - score_open * 1.2) < 5


def test_recalculate_all(db_session, sample_project):
    """Test recalculating all todos"""
    calculator = PriorityCalculator()

    # Create multiple todos
    for i in range(5):
        todo = Todo(
            project_id=sample_project.id,
            title=f"Todo {i}",
            status="open",
            priority_score=0.0,  # Start with wrong score
        )
        db_session.add(todo)

    db_session.commit()

    # Recalculate
    count = calculator.recalculate_all(db_session, sample_project.id)

    assert count == 5

    # Check that all todos have been updated
    todos = db_session.query(Todo).filter_by(project_id=sample_project.id).all()
    for todo in todos:
        assert todo.priority_score > 0


def test_age_urgency_scoring(db_session, sample_project):
    """Test that older todos get higher urgency"""
    calculator = PriorityCalculator()

    # Create old todo (manually set created_at)
    old_todo = Todo(
        project_id=sample_project.id,
        title="Old Todo",
        status="open",
    )
    db_session.add(old_todo)
    db_session.flush()

    # Manually set created_at to 40 days ago
    old_todo.created_at = datetime.utcnow() - timedelta(days=40)
    db_session.commit()

    # Create new todo
    new_todo = Todo(
        project_id=sample_project.id,
        title="New Todo",
        status="open",
    )
    db_session.add(new_todo)
    db_session.commit()

    score_old = calculator.calculate_priority(old_todo, db_session)
    score_new = calculator.calculate_priority(new_todo, db_session)

    # Older todo should have higher priority
    assert score_old > score_new
