"""Local sha cache for resolved GitHub HEADs.

Layout: ``<cache_dir>/<host>/<user>/<tool>`` containing a single 40-char sha.
"""

import os
import re
from pathlib import Path
from typing import Optional

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _cache_dir() -> Path:
    override = os.environ.get("UVX_GH_CACHE_HOME")
    if override:
        return Path(override)
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "uvx-gh"


def _path_for(host: str, user: str, tool: str) -> Path:
    return _cache_dir() / host / user / tool


def read_sha(host: str, user: str, tool: str) -> Optional[str]:
    p = _path_for(host, user, tool)
    if not p.is_file():
        return None
    sha = p.read_text(encoding="utf-8").strip().lower()
    return sha if _SHA_RE.match(sha) else None


def write_sha(host: str, user: str, tool: str, sha: str) -> None:
    p = _path_for(host, user, tool)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(sha + "\n", encoding="utf-8")
