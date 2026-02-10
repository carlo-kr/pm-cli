"""Database manager for PM CLI"""

from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from .models import Base


class DatabaseManager:
    """Manages database connection and session lifecycle"""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize database manager

        Args:
            db_path: Path to SQLite database file. If None, uses default ~/.pm/pm.db
        """
        if db_path is None:
            db_path = self._get_default_db_path()

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create engine with SQLite-specific settings
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            echo=False,  # Set to True for SQL debugging
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        # Enable foreign key constraints for SQLite
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    @staticmethod
    def _get_default_db_path() -> str:
        """Get default database path in user's home directory"""
        home = Path.home()
        return str(home / ".pm" / "pm.db")

    @staticmethod
    def _get_config_dir() -> Path:
        """Get config directory path"""
        return Path.home() / ".pm"

    def init_db(self) -> None:
        """Initialize database by creating all tables"""
        Base.metadata.create_all(bind=self.engine)

    def drop_all(self) -> None:
        """Drop all tables (use with caution!)"""
        Base.metadata.drop_all(bind=self.engine)

    @contextmanager
    def get_session(self):
        """Context manager for database sessions

        Usage:
            with db_manager.get_session() as session:
                project = session.query(Project).first()
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_db_size(self) -> int:
        """Get database file size in bytes"""
        if self.db_path.exists():
            return self.db_path.stat().st_size
        return 0

    def backup_db(self, backup_path: Optional[str] = None) -> str:
        """Create a backup of the database

        Args:
            backup_path: Path for backup file. If None, creates timestamped backup in config dir

        Returns:
            Path to backup file
        """
        import shutil
        from datetime import datetime

        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self._get_config_dir() / f"pm_backup_{timestamp}.db"

        backup_path = Path(backup_path)
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(self.db_path, backup_path)
        return str(backup_path)


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager(db_path: Optional[str] = None) -> DatabaseManager:
    """Get or create global database manager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(db_path)
    return _db_manager


def init_database(db_path: Optional[str] = None) -> DatabaseManager:
    """Initialize database and return manager"""
    db_manager = get_db_manager(db_path)
    db_manager.init_db()
    return db_manager
