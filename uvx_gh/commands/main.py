import os
import re
from typing import List, Optional, Tuple

import typer

from uvx_gh import _cache, _git
from uvx_gh.commands import version_callback

GITHUB_HOST = "github.com"
_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")

helptext = """\
从 github.com/USER/TOOL 拉取并 uvx 运行的薄壳。

\b
用法:
  uvx-gh \\[uvx-options...] USER/TOOL\\[@REF] \\[tool-args...]
  uvx-gh \\[uvx-options...] --user USER TOOL\\[@REF] \\[tool-args...]

\b
后缀语义:
  TOOL         → 使用本地 sha 缓存（首次 git ls-remote 一次后落盘）
  TOOL@latest  → 强制重新解析 HEAD 并刷新缓存
  TOOL@REF     → 作为 git ref 拼到 URL (tag / branch / sha)

\b
缓存位置: $UVX_GH_CACHE_HOME 或 $XDG_CACHE_HOME/uvx-gh
"""

# uvx 中"独立 token 取值"的选项白名单（不带 = 时会吃下一个 argv）。
# 用户可用 `--flag=value` 形式绕过白名单；当 uv 加新选项时维护这里即可。
UVX_VALUE_FLAGS = frozenset(
    {
        "--from",
        "--with",
        "--with-editable",
        "--with-requirements",
        "--python",
        "-p",
        "--refresh-package",
        "--reinstall-package",
        "--upgrade-package",
        "-P",
        "--no-build-package",
        "--no-binary-package",
        "--index",
        "--default-index",
        "--index-url",
        "--extra-index-url",
        "--find-links",
        "--cache-dir",
        "--config-file",
        "--directory",
        "--project",
        "--exclude-newer",
        "--index-strategy",
        "--keyring-provider",
        "--resolution",
        "--prerelease",
        "--link-mode",
        "--color",
    }
)


def split_argv(argv: List[str]) -> Tuple[List[str], Optional[str], List[str]]:
    """把透传过来的 argv 拆成 (uvx_flags, tool_spec, tool_args)。

    第一个非 flag (或 -- 之后的第一个) token 视为 tool_spec, 其后全部归 tool_args。
    含 `=` 的 flag 当成单 token, 不查白名单。
    """
    flags: List[str] = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--":
            tool_spec = argv[i + 1] if i + 1 < len(argv) else None
            tail = argv[i + 2:] if tool_spec is not None else []
            return flags, tool_spec, tail
        if not a.startswith("-"):
            return flags, a, argv[i + 1:]
        if "=" in a or a not in UVX_VALUE_FLAGS:
            flags.append(a)
            i += 1
            continue
        if i + 1 >= len(argv):
            typer.echo(f"uvx-gh: {a} requires a value", err=True)
            raise typer.Exit(1)
        flags.extend([a, argv[i + 1]])
        i += 2
    return flags, None, []


def _validate_name(name: str, kind: str) -> None:
    if name in (".", "..") or not _NAME_RE.match(name):
        typer.echo(f"uvx-gh: invalid {kind} {name!r}", err=True)
        raise typer.Exit(1)


def _resolve_from_url(spec_user: str, tool: str, ref: str) -> str:
    """Build the ``git+https://...`` URL, pinning to a sha when possible.

    - empty ``ref``: use cached sha if present, else ``git ls-remote`` once and cache.
    - ``"latest"``: always re-resolve via ls-remote and overwrite cache.
    - other ``ref`` (tag / branch / sha): pass through unchanged.
    """
    https_url = f"https://{GITHUB_HOST}/{spec_user}/{tool}"
    if not ref:
        sha = _cache.read_sha(GITHUB_HOST, spec_user, tool)
        if sha is None:
            sha = _git.ls_remote_head(https_url)
            _cache.write_sha(GITHUB_HOST, spec_user, tool, sha)
        return f"git+{https_url}@{sha}"
    if ref == "latest":
        sha = _git.ls_remote_head(https_url)
        _cache.write_sha(GITHUB_HOST, spec_user, tool, sha)
        return f"git+{https_url}@{sha}"
    return f"git+{https_url}@{ref}"


def build_uvx_cmd(user: Optional[str], argv: List[str]) -> List[str]:
    """根据透传 argv 构造最终要执行的 uvx 命令向量。

    tool_spec 解析优先级:
      1. ``alice/foo[@ref]`` 短路径（slash 形式）覆盖 ``user``
      2. 否则使用 ``user`` 作为 fallback
      3. 都没有则报错退出
    """
    flags, tool_spec, tool_args = split_argv(argv)

    if not tool_spec:
        typer.echo(
            "Usage: uvx-gh [uvx-options...] <user>/<tool>[@<ref>] [tool-args...]\n"
            "   or: uvx-gh [uvx-options...] --user <user> <tool>[@<ref>] [tool-args...]",
            err=True,
        )
        raise typer.Exit(1)

    tool_part, _, ref = tool_spec.partition("@")

    if "/" in tool_part:
        spec_user, _, tool = tool_part.partition("/")
        if not spec_user or not tool:
            typer.echo(
                f"uvx-gh: invalid tool spec {tool_spec!r}, expected <user>/<tool>[@<ref>]",
                err=True,
            )
            raise typer.Exit(1)
    else:
        if not user:
            typer.echo(
                f"uvx-gh: cannot resolve GitHub user for {tool_spec!r}; "
                "pass <user>/<tool> or --user <user>",
                err=True,
            )
            raise typer.Exit(1)
        spec_user, tool = user, tool_part

    if not tool:
        typer.echo(f"uvx-gh: invalid tool spec {tool_spec!r}", err=True)
        raise typer.Exit(1)

    _validate_name(spec_user, "user")
    _validate_name(tool, "tool")

    from_url = _resolve_from_url(spec_user, tool, ref)
    return ["uvx", *flags, "--from", from_url, tool, *tool_args]


def _version_eager(value: bool) -> None:
    if value:
        version_callback(True, module_name="uvx-gh")


cmd = typer.Typer(add_completion=False)


@cmd.command(
    help=helptext,
    context_settings={
        "ignore_unknown_options": True,
        "allow_extra_args": True,
        "help_option_names": ["-h", "--help"],
    },
)
def main(
    ctx: typer.Context,
    user: Optional[str] = typer.Option(
        None,
        "--user",
        help="GitHub user/org (fallback when tool_spec is not in <user>/<tool> form)",
    ),
    _version: bool = typer.Option(
        False,
        "--version",
        "-v",
        "-V",
        callback=_version_eager,
        is_eager=True,
        help="打印命令版本并退出（不会透传给 uvx）",
    ),
) -> None:
    """从 github.com/<user>/<tool> 拉取并 uvx 运行。"""
    cmd_vec = build_uvx_cmd(user, list(ctx.args))
    try:
        os.execvp(cmd_vec[0], cmd_vec)
    except FileNotFoundError as exc:
        typer.echo(
            f"uvx-gh: 未找到可执行文件 {cmd_vec[0]!r}, 请先安装 uv ({exc})",
            err=True,
        )
        raise typer.Exit(127) from exc


if __name__ == "__main__":
    cmd()
