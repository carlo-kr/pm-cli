"""SQLAlchemy ORM models for the PM CLI database"""

from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import (
    String,
    Integer,
    Float,
    DateTime,
    Date,
    Text,
    JSON,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models"""

    pass


class Project(Base):
    """Represents a project in the workspace"""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    path: Mapped[str] = mapped_column(String(512), unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tech_stack: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default="active"
    )  # active, paused, archived, completed
    priority: Mapped[int] = mapped_column(Integer, default=50)  # 0-100
    has_git: Mapped[bool] = mapped_column(default=False)
    last_activity_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    extra_data: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )  # Extra metadata like commands from CLAUDE.md

    # Relationships
    goals: Mapped[List["Goal"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    todos: Mapped[List["Todo"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    commits: Mapped[List["Commit"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    metrics: Mapped[List["Metric"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Project(name={self.name}, status={self.status}, priority={self.priority})>"


class Goal(Base):
    """Strategic objectives for projects"""

    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50))  # feature, bugfix, refactor, docs, ops
    priority: Mapped[int] = mapped_column(Integer, default=50)  # 0-100
    status: Mapped[str] = mapped_column(
        String(50), default="active"
    )  # active, completed, cancelled
    target_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    parent_goal_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("goals.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="goals")
    todos: Mapped[List["Todo"]] = relationship(back_populates="goal")
    parent_goal: Mapped[Optional["Goal"]] = relationship(
        remote_side=[id], back_populates="sub_goals"
    )
    sub_goals: Mapped[List["Goal"]] = relationship(back_populates="parent_goal")

    def __repr__(self):
        return f"<Goal(title={self.title}, priority={self.priority}, status={self.status})>"


class Todo(Base):
    """Actionable work items derived from goals"""

    __tablename__ = "todos"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    goal_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("goals.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default="open"
    )  # open, in_progress, blocked, completed, cancelled
    priority_score: Mapped[float] = mapped_column(Float, default=50.0)  # Computed priority
    effort_estimate: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # S, M, L, XL
    tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Array of tag strings
    blocked_by: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Array of todo IDs
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="todos")
    goal: Mapped[Optional["Goal"]] = relationship(back_populates="todos")

    # Indexes for common queries
    __table_args__ = (
        Index("ix_todos_status_priority", "status", "priority_score"),
        Index("ix_todos_project_status", "project_id", "status"),
    )

    def __repr__(self):
        return (
            f"<Todo(title={self.title}, status={self.status}, priority={self.priority_score:.1f})>"
        )


class Commit(Base):
    """Git commit tracking for activity correlation"""

    __tablename__ = "commits"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    sha: Mapped[str] = mapped_column(String(40))
    message: Mapped[str] = mapped_column(Text)
    author: Mapped[str] = mapped_column(String(255))
    committed_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    files_changed: Mapped[int] = mapped_column(Integer, default=0)
    insertions: Mapped[int] = mapped_column(Integer, default=0)
    deletions: Mapped[int] = mapped_column(Integer, default=0)
    tags: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )  # Matched todo IDs and other metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="commits")

    # Unique constraint on project + sha
    __table_args__ = (
        UniqueConstraint("project_id", "sha", name="uq_project_commit"),
        Index("ix_commits_project_date", "project_id", "committed_at"),
    )

    def __repr__(self):
        return (
            f"<Commit(sha={self.sha[:7]}, author={self.author}, date={self.committed_at.date()})>"
        )


class Metric(Base):
    """Time-series analytics data"""

    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    metric_type: Mapped[str] = mapped_column(
        String(50)
    )  # commits_per_day, todos_completed, velocity, etc.
    value: Mapped[float] = mapped_column(Float)
    recorded_at: Mapped[date] = mapped_column(Date, index=True)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Additional context
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="metrics")

    # Index for time-series queries
    __table_args__ = (
        Index("ix_metrics_project_type_date", "project_id", "metric_type", "recorded_at"),
    )

    def __repr__(self):
        return f"<Metric(type={self.metric_type}, value={self.value}, date={self.recorded_at})>"


class ActivityLog(Base):
    """Audit trail for all changes"""

    __tablename__ = "activity_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(50))  # project, goal, todo, commit
    entity_id: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(50))  # created, updated, completed, deleted
    details: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )  # Changed fields, old/new values
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<ActivityLog(entity={self.entity_type}, action={self.action}, date={self.created_at})>"
