"""TTL cleanup for stored sessions, honoring settings.session_timeout_minutes.

Session artifacts (uploaded file + JSON outputs) live on disk regardless of
which metadata repository is configured, so expiry is judged per session
directory; the repository is also asked to purge matching metadata rows.
"""

import asyncio
import shutil
import time
from pathlib import Path

from app.core.config import settings
from app.core.logging import AppLogger
from app.storage.base import SessionRepositoryProtocol

logger = AppLogger("CleanupService")


def _expired_dirs(storage_root: Path, ttl_seconds: float) -> list[Path]:
    if not storage_root.exists():
        return []
    cutoff = time.time() - ttl_seconds
    expired = []
    for session_dir in storage_root.iterdir():
        if not session_dir.is_dir():
            continue
        # A session's age is its most recent activity across its uploads.
        newest = max(
            (p.stat().st_mtime for p in session_dir.rglob("*")),
            default=session_dir.stat().st_mtime,
        )
        if newest < cutoff:
            expired.append(session_dir)
    return expired


async def cleanup_expired_sessions(repository: SessionRepositoryProtocol) -> int:
    """Delete session directories (and metadata) older than the TTL.

    Returns the number of sessions removed.
    """
    ttl_seconds = settings.session_timeout_minutes * 60
    storage_root = Path(settings.storage_path).resolve()

    expired = await asyncio.to_thread(_expired_dirs, storage_root, ttl_seconds)
    for session_dir in expired:
        await asyncio.to_thread(shutil.rmtree, session_dir, ignore_errors=True)
        logger.info(f"Removed expired session {session_dir.name}")

    await repository.purge_expired(ttl_seconds)

    if expired:
        logger.info(f"TTL cleanup removed {len(expired)} expired session(s)")
    return len(expired)


async def cleanup_loop(repository: SessionRepositoryProtocol) -> None:
    """Run cleanup on an interval for the life of the app (see main.lifespan)."""
    interval_s = settings.cleanup_interval_minutes * 60
    if interval_s <= 0:
        logger.info("TTL cleanup loop disabled (CLEANUP_INTERVAL_MINUTES=0)")
        return
    while True:
        try:
            await cleanup_expired_sessions(repository)
        except Exception as e:  # never let the loop die on one bad pass
            logger.exception(f"TTL cleanup pass failed: {e}")
        await asyncio.sleep(interval_s)
