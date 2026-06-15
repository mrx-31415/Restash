from __future__ import annotations
import json
import os
import tempfile
from datetime import datetime, timezone

BACKUP_FORMAT_VERSION = 1


def default_backup_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "restash_ratings_backup.json")


def backup_exists(path: str) -> bool:
    return os.path.exists(path)


def collect_ratings(scenes, performers) -> tuple[dict, dict]:
    """id -> rating100 for entities with a non-null native rating. Scenes are light
    dicts (s['rating100']); performers are PerformerData objects (p.rating100)."""
    scene_r = {str(s["id"]): s["rating100"] for s in scenes
               if s.get("rating100") is not None}
    perf_r = {str(p.id): p.rating100 for p in performers
              if p.rating100 is not None}
    return scene_r, perf_r


def _rotate(path: str) -> str:
    """Rename an existing backup to a timestamped sibling. Returns the new path, or
    '' if there was nothing to rotate."""
    if not os.path.exists(path):
        return ""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root, ext = os.path.splitext(path)
    rotated = f"{root}.{ts}{ext}"
    os.replace(path, rotated)
    return rotated


def write_backup(path: str, *, scenes: dict, performers: dict, written_at: str,
                 rotate: bool) -> str:
    """Atomically write the backup (temp file in same dir + os.replace). When
    rotate=True and a backup already exists, rename it to a timestamped sibling
    first. Returns the rotated-away path ('' if none)."""
    rotated = _rotate(path) if rotate else ""
    payload = {
        "format_version": BACKUP_FORMAT_VERSION,
        "written_at": written_at,
        "scenes": scenes,
        "performers": performers,
    }
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".restash_ratings.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(payload, fh)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return rotated


def load_backup(path: str) -> dict | None:
    """Parsed backup, or None if missing/unreadable/corrupt/structurally incomplete."""
    try:
        with open(path) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or "scenes" not in data or "performers" not in data:
        return None
    return data
