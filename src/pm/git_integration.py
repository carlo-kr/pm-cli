"""Git integration for tracking commits and activity"""

import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Set, Tuple

from git import Repo, GitCommandError
from sqlalchemy.orm import Session

from .models import Project, Commit, Todo


class GitScanner:
    """Scans git repositories and syncs commits to database"""

    # Patterns for matching todo references in commit messages
    TODO_PATTERNS = [
        r'#T(\d+)',           # #T42
        r'#(\d+)',            # #42
        r'todo[:\s]+#?(\d+)', # todo: #42, todo 42
        r'fixes?\s+#(\d+)',   # fixes #42, fix #42
        r'closes?\s+#(\d+)',  # closes #42, close #42
        r'resolves?\s+#(\d+)', # resolves #42, resolve #42
    ]

    # Actions that mark todos as completed
    COMPLETION_KEYWORDS = ['fix', 'fixes', 'fixed', 'close', 'closes', 'closed',
                          'resolve', 'resolves', 'resolved', 'complete', 'completes', 'completed']

    def __init__(self):
        """Initialize git scanner"""
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.TODO_PATTERNS]

    def scan_project(self, project: Project, session: Session, limit: Optional[int] = None) -> Tuple[int, int]:
        """Scan a project's git repository and sync commits

        Args:
            project: Project to scan
            session: Database session
            limit: Optional limit on number of commits to fetch (None = all new commits)

        Returns:
            Tuple of (commits_added, todos_updated)
        """
        if not project.has_git:
            return 0, 0

        project_path = Path(project.path)
        if not (project_path / ".git").exists():
            return 0, 0

        try:
            repo = Repo(project_path)
        except GitCommandError:
            return 0, 0

        # Get existing commit SHAs to avoid duplicates
        existing_shas = {
            commit.sha for commit in
            session.query(Commit.sha).filter_by(project_id=project.id).all()
        }

        commits_added = 0
        todos_updated = 0
        latest_commit_date = None

        # Iterate through commits
        for git_commit in repo.iter_commits(max_count=limit):
            if git_commit.hexsha in existing_shas:
                continue  # Skip existing commits

            # Extract todo references and check for completion keywords
            todo_ids, should_complete = self._parse_commit_message(git_commit.message)

            # Get commit stats
            stats = git_commit.stats
            files_changed = len(stats.files)
            insertions = stats.total['insertions']
            deletions = stats.total['deletions']

            # Create commit record
            commit = Commit(
                project_id=project.id,
                sha=git_commit.hexsha,
                message=git_commit.message,
                author=f"{git_commit.author.name} <{git_commit.author.email}>",
                committed_at=datetime.fromtimestamp(git_commit.committed_date),
                files_changed=files_changed,
                insertions=insertions,
                deletions=deletions,
                tags={"todo_ids": list(todo_ids)} if todo_ids else None,
            )

            session.add(commit)
            commits_added += 1

            # Track latest commit date
            commit_date = datetime.fromtimestamp(git_commit.committed_date)
            if latest_commit_date is None or commit_date > latest_commit_date:
                latest_commit_date = commit_date

            # Update linked todos
            if todo_ids:
                for todo_id in todo_ids:
                    todo = session.query(Todo).filter_by(
                        id=todo_id,
                        project_id=project.id
                    ).first()

                    if todo:
                        # Add commit reference to todo's tags
                        if not todo.tags:
                            todo.tags = {}
                        if 'commit_shas' not in todo.tags:
                            todo.tags['commit_shas'] = []

                        if git_commit.hexsha not in todo.tags['commit_shas']:
                            todo.tags['commit_shas'].append(git_commit.hexsha)
                            todo.tags = dict(todo.tags)  # Trigger SQLAlchemy update

                        # Auto-complete if completion keyword found
                        if should_complete and todo.status != "completed":
                            todo.status = "completed"
                            todo.completed_at = commit_date
                            todos_updated += 1

        # Update project's last activity timestamp
        if latest_commit_date:
            if not project.last_activity_at or latest_commit_date > project.last_activity_at:
                project.last_activity_at = latest_commit_date

        session.commit()
        return commits_added, todos_updated

    def _parse_commit_message(self, message: str) -> Tuple[Set[int], bool]:
        """Parse commit message for todo references and completion keywords

        Args:
            message: Commit message text

        Returns:
            Tuple of (set of todo IDs, should_complete_todos)
        """
        todo_ids = set()
        should_complete = False

        # Check for completion keywords
        message_lower = message.lower()
        for keyword in self.COMPLETION_KEYWORDS:
            if keyword in message_lower:
                should_complete = True
                break

        # Extract todo IDs using all patterns
        for pattern in self.compiled_patterns:
            matches = pattern.findall(message)
            for match in matches:
                try:
                    todo_ids.add(int(match))
                except ValueError:
                    continue

        return todo_ids, should_complete

    def get_commit_stats(self, project: Project, session: Session, since: Optional[datetime] = None) -> Dict:
        """Get commit statistics for a project

        Args:
            project: Project to analyze
            session: Database session
            since: Optional date to filter commits

        Returns:
            Dictionary with commit statistics
        """
        query = session.query(Commit).filter_by(project_id=project.id)

        if since:
            query = query.filter(Commit.committed_at >= since)

        commits = query.all()

        if not commits:
            return {
                "total_commits": 0,
                "total_insertions": 0,
                "total_deletions": 0,
                "total_files_changed": 0,
                "unique_authors": 0,
                "avg_insertions": 0,
                "avg_deletions": 0,
            }

        total_insertions = sum(c.insertions for c in commits)
        total_deletions = sum(c.deletions for c in commits)
        total_files = sum(c.files_changed for c in commits)
        unique_authors = len(set(c.author for c in commits))

        return {
            "total_commits": len(commits),
            "total_insertions": total_insertions,
            "total_deletions": total_deletions,
            "total_files_changed": total_files,
            "unique_authors": unique_authors,
            "avg_insertions": total_insertions / len(commits) if commits else 0,
            "avg_deletions": total_deletions / len(commits) if commits else 0,
            "avg_files": total_files / len(commits) if commits else 0,
        }

    def get_activity_timeline(self, project: Project, session: Session,
                             days: int = 30) -> List[Dict]:
        """Get daily commit activity for a project

        Args:
            project: Project to analyze
            session: Database session
            days: Number of days to include in timeline

        Returns:
            List of dicts with date and commit count
        """
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        commits = session.query(Commit).filter(
            Commit.project_id == project.id,
            Commit.committed_at >= cutoff_date
        ).order_by(Commit.committed_at).all()

        # Group by date
        activity_by_date = {}
        for commit in commits:
            date_key = commit.committed_at.date()
            if date_key not in activity_by_date:
                activity_by_date[date_key] = {
                    "date": date_key,
                    "commits": 0,
                    "insertions": 0,
                    "deletions": 0,
                }
            activity_by_date[date_key]["commits"] += 1
            activity_by_date[date_key]["insertions"] += commit.insertions
            activity_by_date[date_key]["deletions"] += commit.deletions

        return sorted(activity_by_date.values(), key=lambda x: x["date"])

    def get_recent_commits(self, project: Project, session: Session,
                          limit: int = 10, author: Optional[str] = None,
                          since: Optional[datetime] = None) -> List[Commit]:
        """Get recent commits for a project

        Args:
            project: Project to query
            session: Database session
            limit: Maximum number of commits to return
            author: Optional author filter
            since: Optional date filter

        Returns:
            List of Commit objects
        """
        query = session.query(Commit).filter_by(project_id=project.id)

        if author:
            query = query.filter(Commit.author.contains(author))

        if since:
            query = query.filter(Commit.committed_at >= since)

        query = query.order_by(Commit.committed_at.desc()).limit(limit)

        return query.all()

    def sync_all_projects(self, session: Session, limit_per_project: Optional[int] = None) -> Dict[str, Tuple[int, int]]:
        """Sync all projects with git repositories

        Args:
            session: Database session
            limit_per_project: Optional limit on commits per project

        Returns:
            Dictionary mapping project name to (commits_added, todos_updated)
        """
        projects = session.query(Project).filter_by(has_git=True).all()

        results = {}
        for project in projects:
            commits_added, todos_updated = self.scan_project(project, session, limit_per_project)
            if commits_added > 0 or todos_updated > 0:
                results[project.name] = (commits_added, todos_updated)

        return results
