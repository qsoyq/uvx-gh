"""Thin wrappers around `git` CLI for HEAD resolution."""

import re
import subprocess

import typer

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def ls_remote_head(https_url: str) -> str:
    """Resolve HEAD sha via ``git ls-remote <url> HEAD``.

    Lightweight: lists refs only, does not fetch objects.
    """
    try:
        result = subprocess.run(
            ["git", "ls-remote", https_url, "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        typer.echo(
            "uvx-gh: git not found on PATH; install git to use uvx-gh",
            err=True,
        )
        raise typer.Exit(127) from exc
    except subprocess.CalledProcessError as exc:
        typer.echo(
            f"uvx-gh: git ls-remote failed for {https_url}\n{exc.stderr.strip()}",
            err=True,
        )
        raise typer.Exit(1) from exc

    line = result.stdout.strip().split("\n", 1)[0] if result.stdout else ""
    sha = line.split("\t", 1)[0].strip().lower() if line else ""
    if not _SHA_RE.match(sha):
        typer.echo(
            f"uvx-gh: cannot parse HEAD from `git ls-remote {https_url}`\n"
            f"Output: {result.stdout!r}",
            err=True,
        )
        raise typer.Exit(1)
    return sha
