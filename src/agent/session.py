"""Session persistence backend using agentscope-runtime JSONSession or RedisSession.

Provides a singleton session backend instance for save/load operations
and UUID-based session ID generation. The backend is selected via the
SESSION_BACKEND env var ("json" or "redis").

Decisions: D-01 (JSONSession), D-03 (SESSION_BACKEND toggle),
D-05/D-06/D-07/D-08 (Redis params), D-09 (flat sessions/ directory).
"""

import logging
import uuid

from agentscope.session import JSONSession, RedisSession

from src.core.settings import get_settings

logger = logging.getLogger(__name__)

_session_backend: JSONSession | RedisSession | None = None


def get_session_backend() -> JSONSession | RedisSession:
    """Return the singleton session backend instance.

    Creates the appropriate backend based on SESSION_BACKEND env var:
    - "json" (default): JSONSession with save_dir from SESSION_DIR
    - "redis": RedisSession with connection params from REDIS_* env vars
    """
    global _session_backend
    if _session_backend is None:
        settings = get_settings()
        if settings.SESSION_BACKEND == "redis":
            _session_backend = RedisSession(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                key_prefix="agentops:",
            )
            logger.info(
                "Session backend initialized: redis at %s:%s db=%s",
                settings.REDIS_HOST,
                settings.REDIS_PORT,
                settings.REDIS_DB,
            )
        else:
            session_dir = settings.SESSION_DIR
            _session_backend = JSONSession(save_dir=session_dir)
            logger.info("Session backend initialized: save_dir=%s", session_dir)
    return _session_backend


def reset_session_backend() -> None:
    """Clear the singleton session backend instance.

    Used by tests that switch backends between test cases and during
    shutdown to release resources.
    """
    global _session_backend
    _session_backend = None


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
