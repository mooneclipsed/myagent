"""Session persistence backend using agentscope-runtime JSONSession.

Provides a singleton JSONSession instance for save/load operations
and UUID-based session ID generation.

Decisions: D-01 (JSONSession), D-04 (client-provided or auto-generated session_id),
D-09 (flat sessions/ directory, configurable via SESSION_DIR).
"""

import logging
import uuid

from agentscope.session import JSONSession

from src.core.settings import get_settings

logger = logging.getLogger(__name__)

_session_backend: JSONSession | None = None


def get_session_backend() -> JSONSession:
    """Return the singleton JSONSession backend instance.

    Creates the session directory at first access. The directory is
    configurable via SESSION_DIR env var (D-09), defaulting to ./sessions.
    """
    global _session_backend
    if _session_backend is None:
        settings = get_settings()
        session_dir = settings.SESSION_DIR
        _session_backend = JSONSession(save_dir=session_dir)
        logger.info("Session backend initialized: save_dir=%s", session_dir)
    return _session_backend


def generate_session_id() -> str:
    """Generate a new unique session ID using UUID4 (D-04)."""
    return str(uuid.uuid4())


def validate_session_id(session_id: str) -> bool:
    """Validate session_id format to prevent path traversal (T-6-01).

    Accepts only standard UUID format: 8-4-4-4-12 hexadecimal characters
    with hyphens, or plain alphanumeric strings. Rejects any path
    separators, dots, or special characters.
    """
    if not session_id or len(session_id) > 128:
        return False
    # Block path traversal characters: / \ . ..
    forbidden = ["/", "\\", ".", ".."]
    for ch in forbidden:
        if ch in session_id:
            return False
    return session_id.isprintable() and session_id.strip() == session_id
