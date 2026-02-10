"""Utility functions for PM CLI"""

import json
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime, date


class Config:
    """Configuration manager for PM CLI"""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize config manager

        Args:
            config_path: Path to config file. If None, uses default ~/.pm/config.json
        """
        if config_path is None:
            config_path = self._get_default_config_path()

        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        self._config: Dict[str, Any] = self._load_config()

    @staticmethod
    def _get_default_config_path() -> str:
        """Get default config path in user's home directory"""
        return str(Path.home() / ".pm" / "config.json")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        if not self.config_path.exists():
            return self._get_default_config()

        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "workspace_path": str(Path.home() / "Building" / "Experiments"),
            "default_priority": 50,
            "default_project_status": "active",
            "auto_sync_on_review": True,
            "show_completed_todos": False,
            "todo_picker_limit": 10,
            "priority_weights": {
                "goal_priority": 0.25,
                "project_priority": 0.15,
                "age_urgency": 0.15,
                "deadline_pressure": 0.20,
                "effort_value": 0.10,
                "git_activity_boost": 0.10,
                "blocking_impact": 0.05,
            },
            "effort_scores": {
                "S": 80,
                "M": 60,
                "L": 40,
                "XL": 20,
            },
        }

    def save(self) -> None:
        """Save configuration to file"""
        with open(self.config_path, "w") as f:
            json.dump(self._config, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set configuration value and save"""
        self._config[key] = value
        self.save()

    def update(self, updates: Dict[str, Any]) -> None:
        """Update multiple configuration values"""
        self._config.update(updates)
        self.save()


def format_datetime(dt: Optional[datetime]) -> str:
    """Format datetime for display"""
    if dt is None:
        return "Never"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_date(d: Optional[date]) -> str:
    """Format date for display"""
    if d is None:
        return "No deadline"
    return d.strftime("%Y-%m-%d")


def parse_date(date_str: str) -> date:
    """Parse date string in various formats"""
    from dateutil import parser

    return parser.parse(date_str).date()


def get_project_name_from_path(path: Path) -> str:
    """Extract project name from path"""
    return path.name


def is_git_repo(path: Path) -> bool:
    """Check if path is a git repository"""
    return (path / ".git").is_dir()


def get_relative_time(dt: datetime) -> str:
    """Get human-readable relative time"""
    now = datetime.utcnow()
    diff = now - dt

    seconds = diff.total_seconds()
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes}m ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours}h ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days}d ago"
    elif seconds < 2592000:
        weeks = int(seconds / 604800)
        return f"{weeks}w ago"
    else:
        months = int(seconds / 2592000)
        return f"{months}mo ago"


def truncate_string(s: str, max_length: int = 50) -> str:
    """Truncate string with ellipsis if too long"""
    if len(s) <= max_length:
        return s
    return s[: max_length - 3] + "..."


def validate_priority(priority: int) -> int:
    """Validate and clamp priority to 0-100 range"""
    return max(0, min(100, priority))


def validate_status(status: str, allowed: list) -> str:
    """Validate status against allowed values"""
    if status not in allowed:
        raise ValueError(f"Invalid status '{status}'. Must be one of: {', '.join(allowed)}")
    return status


# Status constants
PROJECT_STATUSES = ["active", "paused", "archived", "completed"]
GOAL_STATUSES = ["active", "completed", "cancelled"]
TODO_STATUSES = ["open", "in_progress", "blocked", "completed", "cancelled"]
GOAL_CATEGORIES = ["feature", "bugfix", "refactor", "docs", "ops"]
EFFORT_LEVELS = ["S", "M", "L", "XL"]
