"""Priority scoring algorithm for todos"""

from datetime import datetime, date, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from .models import Todo, Commit
from .utils import Config


class PriorityCalculator:
    """Calculates priority scores for todos using multi-factor weighted algorithm"""

    def __init__(self, config: Optional[Config] = None):
        """Initialize calculator with configuration

        Args:
            config: Configuration object with priority weights
        """
        self.config = config or Config()
        self.weights = self.config.get(
            "priority_weights",
            {
                "goal_priority": 0.25,
                "project_priority": 0.15,
                "age_urgency": 0.15,
                "deadline_pressure": 0.20,
                "effort_value": 0.10,
                "git_activity_boost": 0.10,
                "blocking_impact": 0.05,
            },
        )
        self.effort_scores = self.config.get(
            "effort_scores",
            {
                "S": 80,
                "M": 60,
                "L": 40,
                "XL": 20,
            },
        )

    def calculate_priority(self, todo: Todo, session: Session) -> float:
        """Calculate priority score for a todo

        Args:
            todo: Todo object to score
            session: Database session for queries

        Returns:
            Priority score (0-100)
        """
        score = 0.0

        # 1. Goal Priority (25%)
        score += self._goal_priority_score(todo) * self.weights["goal_priority"]

        # 2. Project Priority (15%)
        score += self._project_priority_score(todo) * self.weights["project_priority"]

        # 3. Age Urgency (15%)
        score += self._age_urgency_score(todo) * self.weights["age_urgency"]

        # 4. Deadline Pressure (20%)
        score += self._deadline_pressure_score(todo) * self.weights["deadline_pressure"]

        # 5. Effort Value (10%) - favor quick wins
        score += self._effort_value_score(todo) * self.weights["effort_value"]

        # 6. Git Activity Boost (10%)
        score += self._git_activity_score(todo, session) * self.weights["git_activity_boost"]

        # 7. Blocking Impact (5%)
        score += self._blocking_impact_score(todo, session) * self.weights["blocking_impact"]

        # Apply adjustments
        if todo.status == "blocked":
            score *= 0.5  # Reduce priority for blocked todos
        elif todo.status == "in_progress":
            score *= 1.2  # Boost priority for in-progress (sticky priority)

        # Clamp to 0-100 range
        return max(0.0, min(100.0, score))

    def _goal_priority_score(self, todo: Todo) -> float:
        """Calculate score based on linked goal priority"""
        if todo.goal and todo.goal.priority:
            return float(todo.goal.priority)
        return 50.0  # Default neutral score

    def _project_priority_score(self, todo: Todo) -> float:
        """Calculate score based on project priority"""
        if todo.project and todo.project.priority:
            return float(todo.project.priority)
        return 50.0

    def _age_urgency_score(self, todo: Todo) -> float:
        """Calculate score based on todo age (older = higher urgency)"""
        if not todo.created_at:
            return 30.0

        age_days = (datetime.utcnow() - todo.created_at).days

        if age_days < 1:
            return 20.0
        elif age_days < 3:
            return 30.0
        elif age_days < 7:
            return 50.0
        elif age_days < 14:
            return 70.0
        elif age_days < 30:
            return 80.0
        else:
            return 90.0

    def _deadline_pressure_score(self, todo: Todo) -> float:
        """Calculate score based on deadline proximity (closer = higher pressure)"""
        if not todo.due_date:
            return 30.0  # Low pressure for no deadline

        today = date.today()
        days_until = (todo.due_date - today).days

        if days_until < 0:
            return 100.0  # Overdue - maximum pressure
        elif days_until == 0:
            return 100.0  # Due today
        elif days_until == 1:
            return 95.0  # Due tomorrow
        elif days_until <= 3:
            return 85.0
        elif days_until <= 7:
            return 70.0
        elif days_until <= 14:
            return 50.0
        elif days_until <= 30:
            return 35.0
        else:
            return 20.0

    def _effort_value_score(self, todo: Todo) -> float:
        """Calculate score based on effort estimate (favor quick wins)"""
        if not todo.effort_estimate:
            return 50.0  # Neutral if unknown

        return float(self.effort_scores.get(todo.effort_estimate, 50))

    def _git_activity_score(self, todo: Todo, session: Session) -> float:
        """Calculate score based on recent git activity in project"""
        if not todo.project or not todo.project.has_git:
            return 50.0

        # Check for commits in last 7 days
        cutoff = datetime.utcnow() - timedelta(days=7)
        recent_commits = (
            session.query(Commit)
            .filter(Commit.project_id == todo.project_id, Commit.committed_at >= cutoff)
            .count()
        )

        if recent_commits == 0:
            return 30.0  # Low activity
        elif recent_commits < 5:
            return 60.0
        elif recent_commits < 10:
            return 80.0
        else:
            return 90.0  # High activity

    def _blocking_impact_score(self, todo: Todo, session: Session) -> float:
        """Calculate score based on how many other todos this blocks"""
        if not todo.blocked_by or len(todo.blocked_by.get("todo_ids", [])) == 0:
            # This todo doesn't block anything, check if it blocks others
            blocked_count = (
                session.query(Todo)
                .filter(Todo.project_id == todo.project_id, Todo.status != "completed")
                .all()
            )

            # Count how many todos have this todo in their blocked_by
            blocking_count = 0
            for t in blocked_count:
                if t.blocked_by:
                    blocked_ids = t.blocked_by.get("todo_ids", [])
                    if todo.id in blocked_ids:
                        blocking_count += 1

            # Each blocked todo adds 10 points
            return min(100.0, 50.0 + (blocking_count * 10.0))

        return 50.0

    def recalculate_all(self, session: Session, project_id: Optional[int] = None) -> int:
        """Recalculate priority scores for all todos

        Args:
            session: Database session
            project_id: Optional project ID to limit recalculation

        Returns:
            Number of todos updated
        """
        query = session.query(Todo).filter(Todo.status.in_(["open", "in_progress", "blocked"]))

        if project_id:
            query = query.filter(Todo.project_id == project_id)

        todos = query.all()
        count = 0

        for todo in todos:
            old_score = todo.priority_score
            new_score = self.calculate_priority(todo, session)

            if abs(old_score - new_score) > 0.1:  # Only update if changed significantly
                todo.priority_score = new_score
                count += 1

        session.commit()
        return count
