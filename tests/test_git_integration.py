"""Tests for git integration"""

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pm.models import Base, Project, Commit
from pm.git_integration import GitScanner


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
def scanner():
    """Create a GitScanner instance"""
    return GitScanner()


def test_parse_commit_message_t_notation(scanner):
    """Test parsing #T42 notation"""
    message = "feat: add authentication issue (#T42)"
    todo_ids, should_complete = scanner._parse_commit_message(message)

    assert 42 in todo_ids
    assert should_complete is False  # No completion keyword


def test_parse_commit_message_hash_notation(scanner):
    """Test parsing #42 notation"""
    message = "feat: add new feature #42"
    todo_ids, should_complete = scanner._parse_commit_message(message)

    assert 42 in todo_ids
    assert should_complete is False


def test_parse_commit_message_fixes_keyword(scanner):
    """Test parsing 'fixes #42' notation"""
    message = "fixes #42: broken login"
    todo_ids, should_complete = scanner._parse_commit_message(message)

    assert 42 in todo_ids
    assert should_complete is True  # 'fixes' triggers completion


def test_parse_commit_message_closes_keyword(scanner):
    """Test parsing 'closes #42' notation"""
    message = "closes #42"
    todo_ids, should_complete = scanner._parse_commit_message(message)

    assert 42 in todo_ids
    assert should_complete is True


def test_parse_commit_message_multiple_todos(scanner):
    """Test parsing multiple todo references"""
    message = "feat: implement features for #42 and #43, also fixes #44"
    todo_ids, should_complete = scanner._parse_commit_message(message)

    assert 42 in todo_ids
    assert 43 in todo_ids
    assert 44 in todo_ids
    assert should_complete is True  # 'fixes' present


def test_parse_commit_message_todo_keyword(scanner):
    """Test parsing 'todo: #42' notation"""
    message = "refactor: improve code (todo: #42)"
    todo_ids, should_complete = scanner._parse_commit_message(message)

    assert 42 in todo_ids


def test_parse_commit_message_no_todos(scanner):
    """Test message with no todo references"""
    message = "feat: add new feature"
    todo_ids, should_complete = scanner._parse_commit_message(message)

    assert len(todo_ids) == 0
    assert should_complete is False


def test_parse_commit_message_completion_keywords(scanner):
    """Test all completion keywords"""
    keywords = [
        "fix",
        "fixes",
        "fixed",
        "close",
        "closes",
        "closed",
        "resolve",
        "resolves",
        "resolved",
        "complete",
        "completes",
        "completed",
    ]

    for keyword in keywords:
        message = f"{keyword} #42"
        _, should_complete = scanner._parse_commit_message(message)
        assert should_complete is True, f"Keyword '{keyword}' should trigger completion"


def test_get_commit_stats_empty(scanner, db_session):
    """Test commit stats with no commits"""
    project = Project(name="TestProject", path="/test/path")
    db_session.add(project)
    db_session.commit()

    stats = scanner.get_commit_stats(project, db_session)

    assert stats["total_commits"] == 0
    assert stats["total_insertions"] == 0
    assert stats["unique_authors"] == 0


def test_get_commit_stats_with_commits(scanner, db_session):
    """Test commit stats calculation"""
    project = Project(name="TestProject", path="/test/path", has_git=True)
    db_session.add(project)
    db_session.commit()

    # Add test commits
    commits = [
        Commit(
            project_id=project.id,
            sha="abc123",
            message="Commit 1",
            author="Alice <alice@example.com>",
            committed_at=datetime.now(),
            insertions=100,
            deletions=50,
            files_changed=5,
        ),
        Commit(
            project_id=project.id,
            sha="def456",
            message="Commit 2",
            author="Bob <bob@example.com>",
            committed_at=datetime.now(),
            insertions=200,
            deletions=75,
            files_changed=8,
        ),
    ]

    for commit in commits:
        db_session.add(commit)
    db_session.commit()

    stats = scanner.get_commit_stats(project, db_session)

    assert stats["total_commits"] == 2
    assert stats["total_insertions"] == 300
    assert stats["total_deletions"] == 125
    assert stats["total_files_changed"] == 13
    assert stats["unique_authors"] == 2
    assert stats["avg_insertions"] == 150.0
    assert stats["avg_deletions"] == 62.5


def test_get_commit_stats_with_since_filter(scanner, db_session):
    """Test commit stats with date filtering"""
    from datetime import timedelta

    project = Project(name="TestProject", path="/test/path", has_git=True)
    db_session.add(project)
    db_session.commit()

    now = datetime.now()
    old_date = now - timedelta(days=10)

    # Add old commit
    old_commit = Commit(
        project_id=project.id,
        sha="old123",
        message="Old commit",
        author="Alice <alice@example.com>",
        committed_at=old_date,
        insertions=100,
        deletions=50,
        files_changed=5,
    )

    # Add recent commit
    recent_commit = Commit(
        project_id=project.id,
        sha="new123",
        message="Recent commit",
        author="Alice <alice@example.com>",
        committed_at=now,
        insertions=200,
        deletions=75,
        files_changed=8,
    )

    db_session.add_all([old_commit, recent_commit])
    db_session.commit()

    # Get stats since 5 days ago (should only include recent commit)
    since = now - timedelta(days=5)
    stats = scanner.get_commit_stats(project, db_session, since=since)

    assert stats["total_commits"] == 1
    assert stats["total_insertions"] == 200


def test_get_recent_commits(scanner, db_session):
    """Test getting recent commits"""
    project = Project(name="TestProject", path="/test/path", has_git=True)
    db_session.add(project)
    db_session.commit()

    # Add multiple commits
    for i in range(15):
        commit = Commit(
            project_id=project.id,
            sha=f"sha{i}",
            message=f"Commit {i}",
            author="Alice <alice@example.com>",
            committed_at=datetime.now(),
            insertions=10,
            deletions=5,
            files_changed=2,
        )
        db_session.add(commit)

    db_session.commit()

    # Get recent commits with limit
    commits = scanner.get_recent_commits(project, db_session, limit=10)

    assert len(commits) == 10


def test_get_recent_commits_with_author_filter(scanner, db_session):
    """Test filtering commits by author"""
    project = Project(name="TestProject", path="/test/path", has_git=True)
    db_session.add(project)
    db_session.commit()

    # Add commits from different authors
    alice_commit = Commit(
        project_id=project.id,
        sha="alice123",
        message="Alice's commit",
        author="Alice <alice@example.com>",
        committed_at=datetime.now(),
        insertions=10,
        deletions=5,
        files_changed=2,
    )

    bob_commit = Commit(
        project_id=project.id,
        sha="bob123",
        message="Bob's commit",
        author="Bob <bob@example.com>",
        committed_at=datetime.now(),
        insertions=10,
        deletions=5,
        files_changed=2,
    )

    db_session.add_all([alice_commit, bob_commit])
    db_session.commit()

    # Filter by author
    alice_commits = scanner.get_recent_commits(project, db_session, author="Alice")

    assert len(alice_commits) == 1
    assert "Alice" in alice_commits[0].author
