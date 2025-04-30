import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

from app.core.config import settings


class Session:
    """Represents a user session for file management and mapping operations."""

    def __init__(
        self,
        session_id: str = None,
        created_at: datetime = None,
        file_path: Optional[Path] = None,
        metadata: Optional[Dict] = None,
    ):
        self.session_id = session_id or str(uuid.uuid4())
        self.created_at = created_at or datetime.now()
        self.file_path = file_path
        self.metadata = metadata or {}
        self.expires_at = self.created_at + timedelta(
            hours=settings.SESSION_EXPIRY_HOURS
        )

    @property
    def is_expired(self) -> bool:
        """Check if the session has expired."""
        return datetime.now() > self.expires_at

    @property
    def session_dir(self) -> Path:
        """Get the directory for this session's files."""
        session_dir = settings.UPLOAD_DIR / self.session_id
        session_dir.mkdir(exist_ok=True)
        return session_dir

    def to_dict(self) -> Dict:
        """Convert session to dictionary for storage."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "file_path": str(self.file_path) if self.file_path else None,
            "metadata": self.metadata,
            "expires_at": self.expires_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Session":
        """Create session from dictionary."""
        return cls(
            session_id=data["session_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            file_path=Path(data["file_path"]) if data["file_path"] else None,
            metadata=data["metadata"],
        )


class SessionManager:
    """Manages user sessions for file uploads and mapping jobs."""

    def __init__(self):
        self.sessions: Dict[str, Session] = {}

    def create_session(self) -> Session:
        """Create a new session."""
        session = Session()
        self.sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID.

        First checks in-memory sessions, then tries to recover from disk if not found.
        """
        # Check in-memory sessions first
        session = self.sessions.get(session_id)
        if session:
            if session.is_expired:
                self.delete_session(session_id)
                return None
            return session

        # Session not found in memory, try to recover from disk
        session_dir = settings.UPLOAD_DIR / session_id
        if session_dir.exists():
            # Look for files in the session directory
            files = list(session_dir.glob("*"))
            if files:
                # We found files, recreate the session
                print(f"Recovering session {session_id} from disk")
                file_path = files[0]  # Use the first file found

                # Get file metadata
                metadata = {
                    "file_size": file_path.stat().st_size,
                    "content_type": "text/csv",  # Assume CSV for now
                    "filename": file_path.name,
                }

                # Create and store the recovered session
                session = Session(
                    session_id=session_id,
                    created_at=datetime.fromtimestamp(file_path.stat().st_mtime),
                    file_path=file_path,
                    metadata=metadata,
                )
                self.sessions[session_id] = session
                return session

        # Session truly not found
        return None

    def update_session(self, session_id: str, **kwargs) -> Optional[Session]:
        """Update session properties."""
        session = self.get_session(session_id)
        if not session:
            return None

        for key, value in kwargs.items():
            setattr(session, key, value)

        return session

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its associated files."""
        session = self.sessions.pop(session_id, None)
        if not session:
            return False

        # Clean up session directory
        if session.file_path and session.file_path.exists():
            session.file_path.unlink()

        session_dir = settings.UPLOAD_DIR / session_id
        if session_dir.exists():
            for file in session_dir.iterdir():
                file.unlink()
            session_dir.rmdir()

        return True

    def cleanup_expired(self) -> int:
        """Clean up expired sessions and return count of deleted sessions."""
        expired_ids = [
            sid for sid, session in self.sessions.items() if session.is_expired
        ]
        for sid in expired_ids:
            self.delete_session(sid)
        return len(expired_ids)


# Global session manager instance
session_manager = SessionManager()
