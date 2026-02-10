"""Tests for utility functions"""

import pytest
from datetime import datetime, date
from pm.utils import (
    validate_priority,
    validate_status,
    truncate_string,
    get_relative_time,
    PROJECT_STATUSES,
)


def test_validate_priority():
    """Test priority validation and clamping"""
    assert validate_priority(50) == 50
    assert validate_priority(0) == 0
    assert validate_priority(100) == 100
    assert validate_priority(-10) == 0
    assert validate_priority(150) == 100


def test_validate_status():
    """Test status validation"""
    assert validate_status("active", PROJECT_STATUSES) == "active"
    assert validate_status("paused", PROJECT_STATUSES) == "paused"

    with pytest.raises(ValueError):
        validate_status("invalid", PROJECT_STATUSES)


def test_truncate_string():
    """Test string truncation"""
    assert truncate_string("short", 10) == "short"
    assert truncate_string("this is a very long string", 10) == "this is..."
    assert len(truncate_string("x" * 100, 20)) == 20


def test_get_relative_time():
    """Test relative time formatting"""
    now = datetime.utcnow()

    # Just now
    assert get_relative_time(now) == "just now"

    # Minutes ago
    from datetime import timedelta

    assert "m ago" in get_relative_time(now - timedelta(minutes=5))

    # Hours ago
    assert "h ago" in get_relative_time(now - timedelta(hours=2))

    # Days ago
    assert "d ago" in get_relative_time(now - timedelta(days=3))
