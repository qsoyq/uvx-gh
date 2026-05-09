"""Resolve GitHub HEAD via dulwich (no system git CLI required)."""

import re
from typing import Dict, cast

import typer
from dulwich.client import get_transport_and_path
from dulwich.errors import GitProtocolError, NotGitRepository

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def ls_remote_head(https_url: str) -> str:
    """Resolve HEAD sha for a public HTTPS git repo via smart-HTTP protocol.

    Uses dulwich's pure-Python implementation; does NOT require the system
    `git` binary.
    """
    try:
        client, path = get_transport_and_path(https_url)
        result = client.get_refs(path.encode() if isinstance(path, str) else path)
    except (GitProtocolError, NotGitRepository, OSError) as exc:
        typer.echo(
            f"uvx-gh: failed to resolve HEAD for {https_url}: {exc}",
            err=True,
        )
        raise typer.Exit(1) from exc

    # dulwich >=0.22 returns LsRemoteResult with .refs; older returned a dict.
    refs = cast(Dict[bytes, bytes], getattr(result, "refs", result))
    head = refs.get(b"HEAD")
    if head is None:
        typer.echo(
            f"uvx-gh: no HEAD ref returned for {https_url}",
            err=True,
        )
        raise typer.Exit(1)

    sha = head.decode("ascii", errors="replace").lower()
    if not _SHA_RE.match(sha):
        typer.echo(
            f"uvx-gh: invalid HEAD sha {sha!r} for {https_url}",
            err=True,
        )
        raise typer.Exit(1)
    return sha
