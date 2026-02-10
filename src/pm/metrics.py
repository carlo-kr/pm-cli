"""Metrics calculation and analytics for projects"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from sqlalchemy import func
from sqlalchemy.orm import Session

from .models import Project, Goal, Todo, Commit, Metric


class MetricsCalculator:
    """Calculates and tracks various project metrics"""

    def __init__(self):
        """Initialize metrics calculator"""
        pass

    def calculate_velocity(self, project: Project, session: Session, days: int = 7) -> float:
        """Calculate todo completion velocity (todos/day)

        Args:
            project: Project to analyze
            session: Database session
            days: Number of days to analyze

        Returns:
            Average todos completed per day
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        completed_count = session.query(Todo).filter(
            Todo.project_id == project.id,
            Todo.status == "completed",
            Todo.completed_at >= cutoff
        ).count()

        return completed_count / days if days > 0 else 0

    def calculate_completion_rate(self, project: Project, session: Session) -> float:
        """Calculate overall completion rate (0-100%)

        Args:
            project: Project to analyze
            session: Database session

        Returns:
            Completion rate as percentage
        """
        total = session.query(Todo).filter_by(project_id=project.id).count()

        if total == 0:
            return 0.0

        completed = session.query(Todo).filter(
            Todo.project_id == project.id,
            Todo.status == "completed"
        ).count()

        return (completed / total) * 100

    def calculate_health_score(self, project: Project, session: Session) -> Tuple[float, str]:
        """Calculate project health score (0-100) with status

        Factors:
        - Recent activity (commits, todo completions)
        - Completion rate
        - Overdue todos
        - Blocked todos
        - Goal progress

        Args:
            project: Project to analyze
            session: Database session

        Returns:
            Tuple of (score, status_text)
        """
        score = 0.0

        # 1. Recent activity (30 points)
        cutoff_week = datetime.utcnow() - timedelta(days=7)
        cutoff_month = datetime.utcnow() - timedelta(days=30)

        recent_commits = session.query(Commit).filter(
            Commit.project_id == project.id,
            Commit.committed_at >= cutoff_week
        ).count()

        recent_todos = session.query(Todo).filter(
            Todo.project_id == project.id,
            Todo.completed_at >= cutoff_week
        ).count()

        if recent_commits > 5 or recent_todos > 3:
            score += 30
        elif recent_commits > 0 or recent_todos > 0:
            score += 20
        elif project.last_activity_at and project.last_activity_at >= cutoff_month:
            score += 10

        # 2. Completion rate (25 points)
        completion_rate = self.calculate_completion_rate(project, session)
        score += (completion_rate / 100) * 25

        # 3. No overdue todos (20 points)
        today = date.today()
        overdue_count = session.query(Todo).filter(
            Todo.project_id == project.id,
            Todo.status.in_(["open", "in_progress"]),
            Todo.due_date < today
        ).count()

        if overdue_count == 0:
            score += 20
        elif overdue_count <= 2:
            score += 10

        # 4. No blocked todos (15 points)
        blocked_count = session.query(Todo).filter(
            Todo.project_id == project.id,
            Todo.status == "blocked"
        ).count()

        if blocked_count == 0:
            score += 15
        elif blocked_count <= 1:
            score += 8

        # 5. Goal progress (10 points)
        active_goals = session.query(Goal).filter(
            Goal.project_id == project.id,
            Goal.status == "active"
        ).count()

        if active_goals > 0:
            # Check if goals have todos and some are completed
            goals_with_progress = 0
            for goal in session.query(Goal).filter(
                Goal.project_id == project.id,
                Goal.status == "active"
            ).all():
                if len(goal.todos) > 0:
                    completed = sum(1 for t in goal.todos if t.status == "completed")
                    if completed > 0:
                        goals_with_progress += 1

            if goals_with_progress > 0:
                score += 10

        # Determine status text
        if score >= 80:
            status = "Excellent"
        elif score >= 60:
            status = "Good"
        elif score >= 40:
            status = "Fair"
        elif score >= 20:
            status = "Needs Attention"
        else:
            status = "Critical"

        return round(score, 1), status

    def get_todo_breakdown(self, project: Project, session: Session) -> Dict[str, int]:
        """Get breakdown of todos by status

        Args:
            project: Project to analyze
            session: Database session

        Returns:
            Dictionary mapping status to count
        """
        breakdown = {
            "open": 0,
            "in_progress": 0,
            "blocked": 0,
            "completed": 0,
            "cancelled": 0,
        }

        results = session.query(Todo.status, func.count(Todo.id)).filter(
            Todo.project_id == project.id
        ).group_by(Todo.status).all()

        for status, count in results:
            if status in breakdown:
                breakdown[status] = count

        return breakdown

    def get_goal_breakdown(self, project: Project, session: Session) -> Dict[str, int]:
        """Get breakdown of goals by status

        Args:
            project: Project to analyze
            session: Database session

        Returns:
            Dictionary mapping status to count
        """
        breakdown = {
            "active": 0,
            "completed": 0,
            "cancelled": 0,
        }

        results = session.query(Goal.status, func.count(Goal.id)).filter(
            Goal.project_id == project.id
        ).group_by(Goal.status).all()

        for status, count in results:
            if status in breakdown:
                breakdown[status] = count

        return breakdown

    def get_overdue_todos(self, project: Project, session: Session) -> List[Todo]:
        """Get list of overdue todos

        Args:
            project: Project to analyze
            session: Database session

        Returns:
            List of overdue Todo objects
        """
        today = date.today()

        return session.query(Todo).filter(
            Todo.project_id == project.id,
            Todo.status.in_(["open", "in_progress"]),
            Todo.due_date < today
        ).order_by(Todo.due_date).all()

    def get_upcoming_deadlines(self, project: Project, session: Session, days: int = 7) -> List[Todo]:
        """Get todos with upcoming deadlines

        Args:
            project: Project to analyze
            session: Database session
            days: Number of days to look ahead

        Returns:
            List of Todo objects with upcoming deadlines
        """
        today = date.today()
        future = today + timedelta(days=days)

        return session.query(Todo).filter(
            Todo.project_id == project.id,
            Todo.status.in_(["open", "in_progress"]),
            Todo.due_date >= today,
            Todo.due_date <= future
        ).order_by(Todo.due_date).all()

    def get_velocity_trend(self, project: Project, session: Session, weeks: int = 4) -> List[Dict]:
        """Get velocity trend over time (weekly)

        Args:
            project: Project to analyze
            session: Database session
            weeks: Number of weeks to analyze

        Returns:
            List of dicts with week start date and velocity
        """
        trend = []
        today = date.today()

        for i in range(weeks):
            week_end = today - timedelta(days=i * 7)
            week_start = week_end - timedelta(days=7)

            completed_count = session.query(Todo).filter(
                Todo.project_id == project.id,
                Todo.status == "completed",
                Todo.completed_at >= datetime.combine(week_start, datetime.min.time()),
                Todo.completed_at < datetime.combine(week_end, datetime.min.time())
            ).count()

            trend.append({
                "week_start": week_start,
                "week_end": week_end,
                "velocity": completed_count / 7,
                "todos_completed": completed_count,
            })

        return list(reversed(trend))

    def calculate_burn_down(self, goal: Goal, session: Session) -> Dict:
        """Calculate burn-down data for a goal

        Args:
            goal: Goal to analyze
            session: Database session

        Returns:
            Dictionary with burn-down metrics
        """
        total_todos = len(goal.todos)
        completed_todos = sum(1 for t in goal.todos if t.status == "completed")
        remaining_todos = total_todos - completed_todos

        # Calculate progress percentage
        progress = (completed_todos / total_todos * 100) if total_todos > 0 else 0

        # Calculate days remaining if target date exists
        days_remaining = None
        if goal.target_date:
            days_remaining = (goal.target_date - date.today()).days

        # Estimate completion date based on velocity
        estimated_completion = None
        if remaining_todos > 0:
            velocity = self.calculate_velocity(goal.project, session, days=14)
            if velocity > 0:
                days_needed = remaining_todos / velocity
                estimated_completion = date.today() + timedelta(days=days_needed)

        return {
            "total_todos": total_todos,
            "completed_todos": completed_todos,
            "remaining_todos": remaining_todos,
            "progress": round(progress, 1),
            "days_remaining": days_remaining,
            "estimated_completion": estimated_completion,
            "on_track": self._is_goal_on_track(goal, completed_todos, total_todos),
        }

    def _is_goal_on_track(self, goal: Goal, completed: int, total: int) -> Optional[bool]:
        """Determine if goal is on track to meet target date

        Args:
            goal: Goal to analyze
            completed: Number of completed todos
            total: Total number of todos

        Returns:
            True if on track, False if behind, None if no target date
        """
        if not goal.target_date or total == 0:
            return None

        today = date.today()
        if goal.target_date < today:
            return False  # Already overdue

        # Calculate expected progress
        if goal.created_at:
            total_days = (goal.target_date - goal.created_at.date()).days
            elapsed_days = (today - goal.created_at.date()).days

            if total_days > 0:
                expected_progress = elapsed_days / total_days
                actual_progress = completed / total

                return actual_progress >= expected_progress * 0.9  # 90% threshold

        return None

    def store_daily_metrics(self, project: Project, session: Session) -> None:
        """Store daily metrics snapshot for trend analysis

        Args:
            project: Project to store metrics for
            session: Database session
        """
        today = date.today()

        # Check if metrics already exist for today
        existing = session.query(Metric).filter(
            Metric.project_id == project.id,
            Metric.recorded_at == today
        ).first()

        if existing:
            return  # Already recorded today

        # Calculate metrics
        velocity = self.calculate_velocity(project, session, days=7)
        completion_rate = self.calculate_completion_rate(project, session)
        health_score, _ = self.calculate_health_score(project, session)

        todo_breakdown = self.get_todo_breakdown(project, session)

        # Store metrics
        metrics_to_store = [
            Metric(
                project_id=project.id,
                metric_type="velocity",
                value=velocity,
                recorded_at=today,
            ),
            Metric(
                project_id=project.id,
                metric_type="completion_rate",
                value=completion_rate,
                recorded_at=today,
            ),
            Metric(
                project_id=project.id,
                metric_type="health_score",
                value=health_score,
                recorded_at=today,
            ),
            Metric(
                project_id=project.id,
                metric_type="todos_open",
                value=todo_breakdown["open"],
                recorded_at=today,
            ),
            Metric(
                project_id=project.id,
                metric_type="todos_completed",
                value=todo_breakdown["completed"],
                recorded_at=today,
            ),
        ]

        for metric in metrics_to_store:
            session.add(metric)

        session.commit()

    def get_metric_history(self, project: Project, session: Session,
                          metric_type: str, days: int = 30) -> List[Tuple[date, float]]:
        """Get historical metric values

        Args:
            project: Project to query
            session: Database session
            metric_type: Type of metric to retrieve
            days: Number of days of history

        Returns:
            List of (date, value) tuples
        """
        cutoff = date.today() - timedelta(days=days)

        metrics = session.query(Metric).filter(
            Metric.project_id == project.id,
            Metric.metric_type == metric_type,
            Metric.recorded_at >= cutoff
        ).order_by(Metric.recorded_at).all()

        return [(m.recorded_at, m.value) for m in metrics]
