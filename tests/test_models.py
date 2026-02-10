"""Tests for database models"""

import pytest
from datetime import datetime, date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pm.models import Base, Project, Goal, Todo, Commit, Metric


@pytest.fixture
def db_session():
    """Create an in-memory database for testing"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def test_create_project(db_session):
    """Test creating a project"""
    project = Project(
        name="TestProject",
        path="/test/path",
        status="active",
        priority=80,
        has_git=True,
    )
    db_session.add(project)
    db_session.commit()

    assert project.id is not None
    assert project.name == "TestProject"
    assert project.priority == 80
    assert project.has_git is True


def test_create_goal_with_project(db_session):
    """Test creating a goal linked to a project"""
    project = Project(name="TestProject", path="/test/path")
    db_session.add(project)
    db_session.commit()

    goal = Goal(
        project_id=project.id,
        title="Test Goal",
        description="Test description",
        category="feature",
        priority=90,
        status="active",
    )
    db_session.add(goal)
    db_session.commit()

    assert goal.id is not None
    assert goal.project_id == project.id
    assert goal.title == "Test Goal"
    assert len(project.goals) == 1


def test_create_todo_with_goal(db_session):
    """Test creating a todo linked to a goal"""
    project = Project(name="TestProject", path="/test/path")
    db_session.add(project)
    db_session.commit()

    goal = Goal(
        project_id=project.id,
        title="Test Goal",
        category="feature",
        priority=90,
    )
    db_session.add(goal)
    db_session.commit()

    todo = Todo(
        project_id=project.id,
        goal_id=goal.id,
        title="Test Todo",
        status="open",
        effort_estimate="M",
    )
    db_session.add(todo)
    db_session.commit()

    assert todo.id is not None
    assert todo.project_id == project.id
    assert todo.goal_id == goal.id
    assert len(project.todos) == 1
    assert len(goal.todos) == 1


def test_cascade_delete_project(db_session):
    """Test that deleting a project cascades to goals and todos"""
    project = Project(name="TestProject", path="/test/path")
    db_session.add(project)
    db_session.commit()

    goal = Goal(project_id=project.id, title="Test Goal", category="feature", priority=90)
    todo = Todo(project_id=project.id, goal_id=None, title="Test Todo", status="open")
    db_session.add_all([goal, todo])
    db_session.commit()

    project_id = project.id

    # Delete project
    db_session.delete(project)
    db_session.commit()

    # Verify goals and todos are deleted
    assert db_session.query(Goal).filter_by(project_id=project_id).count() == 0
    assert db_session.query(Todo).filter_by(project_id=project_id).count() == 0
