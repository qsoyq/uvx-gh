import os

import pytest
import typer
from dulwich.errors import GitProtocolError
from typer.testing import CliRunner

from uvx_gh import _cache, _git
from uvx_gh.commands.main import build_uvx_cmd, cmd, split_argv

FAKE_SHA = "1234567890abcdef1234567890abcdef12345678"
FAKE_SHA2 = "abcdef0123456789abcdef0123456789abcdef01"


@pytest.fixture(autouse=True)
def _isolate_cache(tmp_path, monkeypatch):
    """Per-test cache isolation: redirect via UVX_GH_CACHE_HOME env var."""
    monkeypatch.setenv("UVX_GH_CACHE_HOME", str(tmp_path / "uvx-gh-cache"))


@pytest.fixture
def fake_head(monkeypatch):
    """Replace ls_remote_head with a deterministic fake; return the sha."""
    monkeypatch.setattr(_git, "ls_remote_head", lambda url: FAKE_SHA)
    return FAKE_SHA


@pytest.fixture
def uvx_on_path(monkeypatch):
    """Make the pre-flight `shutil.which('uvx')` always succeed."""
    import uvx_gh.commands.main as main_mod

    monkeypatch.setattr(main_mod.shutil, "which", lambda name: f"/fake/bin/{name}")


# ---------- split_argv ----------


def test_split_argv_only_tool():
    flags, tool, tail = split_argv(["foo"])
    assert flags == []
    assert tool == "foo"
    assert tail == []


def test_split_argv_empty():
    flags, tool, tail = split_argv([])
    assert flags == []
    assert tool is None
    assert tail == []


def test_split_argv_simple_flag_then_tool():
    flags, tool, tail = split_argv(["--refresh", "foo"])
    assert flags == ["--refresh"]
    assert tool == "foo"
    assert tail == []


def test_split_argv_value_flag_consumes_next_token():
    flags, tool, tail = split_argv(["--with", "extras", "foo"])
    assert flags == ["--with", "extras"]
    assert tool == "foo"
    assert tail == []


def test_split_argv_short_value_flag():
    flags, tool, tail = split_argv(["-p", "3.12", "foo"])
    assert flags == ["-p", "3.12"]
    assert tool == "foo"
    assert tail == []


def test_split_argv_equals_form_skips_whitelist_lookup():
    flags, tool, tail = split_argv(["--with=extras", "foo"])
    assert flags == ["--with=extras"]
    assert tool == "foo"
    assert tail == []


def test_split_argv_unknown_flag_is_single_token():
    flags, tool, tail = split_argv(["--no-progress", "foo"])
    assert flags == ["--no-progress"]
    assert tool == "foo"
    assert tail == []


def test_split_argv_tool_args_after_tool():
    flags, tool, tail = split_argv(["foo", "--tool-flag", "value"])
    assert flags == []
    assert tool == "foo"
    assert tail == ["--tool-flag", "value"]


def test_split_argv_double_dash_terminator():
    flags, tool, tail = split_argv(["--", "some-tool", "--user", "actually-tool-arg"])
    assert flags == []
    assert tool == "some-tool"
    assert tail == ["--user", "actually-tool-arg"]


def test_split_argv_double_dash_with_no_tail():
    flags, tool, tail = split_argv(["--"])
    assert flags == []
    assert tool is None
    assert tail == []


def test_split_argv_value_flag_missing_value_raises_exit():
    with pytest.raises(typer.Exit) as exc_info:
        split_argv(["--with"])
    assert exc_info.value.exit_code == 1


def test_split_argv_mixed_flags_then_tool_then_tool_args():
    flags, tool, tail = split_argv(["--refresh", "--python", "3.12", "foo", "--tool-arg"])
    assert flags == ["--refresh", "--python", "3.12"]
    assert tool == "foo"
    assert tail == ["--tool-arg"]


# ---------- build_uvx_cmd: short-path + --user fallback ----------


def test_build_uvx_cmd_short_path_plain(fake_head):
    """No ref → cache miss → ls-remote → pinned URL with resolved sha."""
    result = build_uvx_cmd(None, ["alice/foo"])
    assert result == [
        "uvx",
        "--from",
        f"git+https://github.com/alice/foo@{fake_head}",
        "foo",
    ]


def test_build_uvx_cmd_short_path_at_latest_pins_to_resolved_sha(fake_head):
    """@latest re-resolves and pins URL — no longer adds --refresh flag."""
    result = build_uvx_cmd(None, ["alice/foo@latest"])
    assert result == [
        "uvx",
        "--from",
        f"git+https://github.com/alice/foo@{fake_head}",
        "foo",
    ]


def test_build_uvx_cmd_short_path_at_explicit_ref_passthrough():
    """Explicit @v1.2.3 bypasses cache and ls-remote entirely."""
    result = build_uvx_cmd(None, ["alice/foo@v1.2.3"])
    assert result == [
        "uvx",
        "--from",
        "git+https://github.com/alice/foo@v1.2.3",
        "foo",
    ]


def test_build_uvx_cmd_user_fallback_when_no_short_path(fake_head):
    result = build_uvx_cmd("alice", ["foo"])
    assert result == [
        "uvx",
        "--from",
        f"git+https://github.com/alice/foo@{fake_head}",
        "foo",
    ]


def test_build_uvx_cmd_short_path_overrides_user_fallback(fake_head):
    result = build_uvx_cmd("bob", ["alice/foo"])
    assert result == [
        "uvx",
        "--from",
        f"git+https://github.com/alice/foo@{fake_head}",
        "foo",
    ]


def test_build_uvx_cmd_no_user_no_short_path_exits():
    with pytest.raises(typer.Exit) as exc_info:
        build_uvx_cmd(None, ["foo"])
    assert exc_info.value.exit_code == 1


def test_build_uvx_cmd_passes_uvx_flags_and_tool_args(fake_head):
    result = build_uvx_cmd(None, ["--refresh", "alice/foo", "--port", "8080"])
    assert result == [
        "uvx",
        "--refresh",
        "--from",
        f"git+https://github.com/alice/foo@{fake_head}",
        "foo",
        "--port",
        "8080",
    ]


def test_build_uvx_cmd_no_tool_exits():
    with pytest.raises(typer.Exit) as exc_info:
        build_uvx_cmd("alice", ["--refresh"])
    assert exc_info.value.exit_code == 1


def test_build_uvx_cmd_double_dash_lets_tool_have_dashed_name(fake_head):
    result = build_uvx_cmd(None, ["--", "alice/tool", "--user", "bob"])
    assert result == [
        "uvx",
        "--from",
        f"git+https://github.com/alice/tool@{fake_head}",
        "tool",
        "--user",
        "bob",
    ]


@pytest.mark.parametrize("bad_spec", ["alice/", "/foo", "/"])
def test_build_uvx_cmd_invalid_short_path_exits(bad_spec):
    with pytest.raises(typer.Exit):
        build_uvx_cmd(None, [bad_spec])


@pytest.mark.parametrize(
    "bad_name",
    ["foo/bar", "foo bar", "foo;bar", ".", "..", "foo$bar"],
)
def test_build_uvx_cmd_rejects_path_traversal_and_special_chars(bad_name):
    with pytest.raises(typer.Exit):
        build_uvx_cmd(None, [f"alice/{bad_name}"])
    with pytest.raises(typer.Exit):
        build_uvx_cmd(bad_name, ["foo"])


# ---------- extras (PEP 508) ----------


def test_build_uvx_cmd_extras_short_path(fake_head):
    """alice/foo[bar] → --from "foo[bar] @ git+...@<sha>"."""
    result = build_uvx_cmd(None, ["alice/foo[bar]"])
    assert result == [
        "uvx",
        "--from",
        f"foo[bar] @ git+https://github.com/alice/foo@{fake_head}",
        "foo",
    ]


def test_build_uvx_cmd_extras_with_at_latest(fake_head):
    result = build_uvx_cmd(None, ["alice/foo[bar]@latest"])
    assert result == [
        "uvx",
        "--from",
        f"foo[bar] @ git+https://github.com/alice/foo@{fake_head}",
        "foo",
    ]


def test_build_uvx_cmd_extras_with_explicit_ref():
    result = build_uvx_cmd(None, ["alice/foo[bar]@v1.2.3"])
    assert result == [
        "uvx",
        "--from",
        "foo[bar] @ git+https://github.com/alice/foo@v1.2.3",
        "foo",
    ]


def test_build_uvx_cmd_multiple_extras(fake_head):
    result = build_uvx_cmd(None, ["alice/foo[bar,baz]"])
    assert result == [
        "uvx",
        "--from",
        f"foo[bar,baz] @ git+https://github.com/alice/foo@{fake_head}",
        "foo",
    ]


def test_build_uvx_cmd_extras_with_user_fallback(fake_head):
    result = build_uvx_cmd("alice", ["foo[bar]"])
    assert result == [
        "uvx",
        "--from",
        f"foo[bar] @ git+https://github.com/alice/foo@{fake_head}",
        "foo",
    ]


def test_extras_share_sha_cache_with_bare_call(monkeypatch):
    """Different extras of the same repo must hit the same sha cache entry."""
    calls = []

    def counting_ls_remote(url):
        calls.append(url)
        return FAKE_SHA

    monkeypatch.setattr(_git, "ls_remote_head", counting_ls_remote)

    build_uvx_cmd(None, ["alice/foo"])
    build_uvx_cmd(None, ["alice/foo[bar]"])
    build_uvx_cmd(None, ["alice/foo[baz,qux]"])

    assert calls == ["https://github.com/alice/foo"]


@pytest.mark.parametrize(
    "bad_spec",
    [
        "alice/foo[]",
        "alice/foo[bar,]",
        "alice/foo[,bar]",
        "alice/foo[bar baz]",
        "alice/foo[bar;rm]",
    ],
)
def test_build_uvx_cmd_invalid_extras_exits(bad_spec):
    with pytest.raises(typer.Exit):
        build_uvx_cmd(None, [bad_spec])


# ---------- --no-git: tarball URL emission ----------


def test_build_uvx_cmd_no_git_uses_tarball_with_resolved_sha(fake_head):
    """no_git=True with cache miss → archive tarball pinned to resolved sha."""
    result = build_uvx_cmd(None, ["alice/foo"], no_git=True)
    assert result == [
        "uvx",
        "--from",
        f"https://github.com/alice/foo/archive/{fake_head}.tar.gz",
        "foo",
    ]


def test_build_uvx_cmd_no_git_at_latest_pins_tarball_to_resolved_sha(fake_head):
    result = build_uvx_cmd(None, ["alice/foo@latest"], no_git=True)
    assert result == [
        "uvx",
        "--from",
        f"https://github.com/alice/foo/archive/{fake_head}.tar.gz",
        "foo",
    ]


def test_build_uvx_cmd_no_git_explicit_ref_passthrough():
    result = build_uvx_cmd(None, ["alice/foo@v1.2.3"], no_git=True)
    assert result == [
        "uvx",
        "--from",
        "https://github.com/alice/foo/archive/v1.2.3.tar.gz",
        "foo",
    ]


def test_build_uvx_cmd_no_git_url_encodes_slashes_in_ref():
    """branch names with `/` must be percent-encoded so the URL stays well-formed."""
    result = build_uvx_cmd(None, ["alice/foo@release/1.x"], no_git=True)
    assert result == [
        "uvx",
        "--from",
        "https://github.com/alice/foo/archive/release%2F1.x.tar.gz",
        "foo",
    ]


def test_build_uvx_cmd_no_git_extras(fake_head):
    result = build_uvx_cmd(None, ["alice/foo[bar]"], no_git=True)
    assert result == [
        "uvx",
        "--from",
        f"foo[bar] @ https://github.com/alice/foo/archive/{fake_head}.tar.gz",
        "foo",
    ]


def test_build_uvx_cmd_no_git_default_false_emits_git_https(fake_head):
    """Sanity: omitting no_git keeps the existing git+https behavior."""
    result = build_uvx_cmd(None, ["alice/foo"])
    assert result[2].startswith("git+https://")


def test_cli_no_git_flag_end_to_end(fake_head, uvx_on_path, monkeypatch):
    captured: dict = {}
    monkeypatch.setattr(os, "execvp", _make_fake_execvp(captured))

    result = CliRunner().invoke(cmd, ["--no-git", "alice/foo"])

    assert isinstance(result.exception, _ExecCalled), result.output
    assert captured["args"] == [
        "uvx",
        "--from",
        f"https://github.com/alice/foo/archive/{fake_head}.tar.gz",
        "foo",
    ]


def test_cli_no_git_via_env_var(fake_head, uvx_on_path, monkeypatch):
    """UVX_GH_NO_GIT=1 should toggle --no-git without the flag."""
    captured: dict = {}
    monkeypatch.setattr(os, "execvp", _make_fake_execvp(captured))
    monkeypatch.setenv("UVX_GH_NO_GIT", "1")

    result = CliRunner().invoke(cmd, ["alice/foo"])

    assert isinstance(result.exception, _ExecCalled), result.output
    assert captured["args"][2] == f"https://github.com/alice/foo/archive/{fake_head}.tar.gz"


# ---------- cache hit/miss interaction with build_uvx_cmd ----------


def test_cache_hit_skips_ls_remote(monkeypatch):
    cached_sha = FAKE_SHA2
    _cache.write_sha("github.com", "alice", "foo", cached_sha)

    def fail_ls_remote(url):
        raise AssertionError(f"ls-remote should not run on cache hit (got {url})")

    monkeypatch.setattr(_git, "ls_remote_head", fail_ls_remote)

    result = build_uvx_cmd(None, ["alice/foo"])
    assert result[2] == f"git+https://github.com/alice/foo@{cached_sha}"


def test_cache_miss_resolves_and_persists(fake_head):
    assert _cache.read_sha("github.com", "alice", "foo") is None
    build_uvx_cmd(None, ["alice/foo"])
    assert _cache.read_sha("github.com", "alice", "foo") == fake_head


def test_at_latest_overwrites_existing_cache(monkeypatch):
    _cache.write_sha("github.com", "alice", "foo", "0" * 40)
    new_sha = FAKE_SHA
    calls = []

    def fake_ls_remote(url):
        calls.append(url)
        return new_sha

    monkeypatch.setattr(_git, "ls_remote_head", fake_ls_remote)

    result = build_uvx_cmd(None, ["alice/foo@latest"])
    assert calls == ["https://github.com/alice/foo"]
    assert _cache.read_sha("github.com", "alice", "foo") == new_sha
    assert result[2] == f"git+https://github.com/alice/foo@{new_sha}"


def test_explicit_ref_bypasses_cache_and_ls_remote(monkeypatch):
    monkeypatch.setattr(
        _git,
        "ls_remote_head",
        lambda url: pytest.fail(f"should not run for explicit ref (got {url})"),
    )
    result = build_uvx_cmd(None, ["alice/foo@v1.2.3"])
    assert result[2] == "git+https://github.com/alice/foo@v1.2.3"
    assert _cache.read_sha("github.com", "alice", "foo") is None


# ---------- _cache module ----------


def test_cache_read_missing_returns_none():
    assert _cache.read_sha("github.com", "nobody", "nothing") is None


def test_cache_roundtrip():
    _cache.write_sha("github.com", "alice", "foo", FAKE_SHA)
    assert _cache.read_sha("github.com", "alice", "foo") == FAKE_SHA


def test_cache_overwrite():
    _cache.write_sha("github.com", "alice", "foo", "a" * 40)
    _cache.write_sha("github.com", "alice", "foo", "b" * 40)
    assert _cache.read_sha("github.com", "alice", "foo") == "b" * 40


def test_cache_read_invalid_content_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv("UVX_GH_CACHE_HOME", str(tmp_path))
    p = tmp_path / "github.com" / "alice" / "foo"
    p.parent.mkdir(parents=True)
    p.write_text("not-a-sha\n")
    assert _cache.read_sha("github.com", "alice", "foo") is None


def test_cache_dir_respects_uvx_gh_cache_home(monkeypatch, tmp_path):
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    monkeypatch.setenv("UVX_GH_CACHE_HOME", str(tmp_path / "custom"))
    assert _cache._cache_dir() == tmp_path / "custom"


def test_cache_dir_falls_back_to_xdg(monkeypatch, tmp_path):
    monkeypatch.delenv("UVX_GH_CACHE_HOME", raising=False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
    assert _cache._cache_dir() == tmp_path / "xdg" / "uvx-gh"


# ---------- _git module (dulwich-mocked) ----------


class _FakeLsRemoteResult:
    def __init__(self, refs: dict):
        self.refs = refs


class _FakeClient:
    def __init__(self, refs=None, raises=None):
        self._refs = refs or {}
        self._raises = raises

    def get_refs(self, path):
        if self._raises is not None:
            raise self._raises
        return _FakeLsRemoteResult(self._refs)


def _patch_dulwich(monkeypatch, *, refs=None, raises=None):
    fake = _FakeClient(refs=refs, raises=raises)
    monkeypatch.setattr(
        _git,
        "get_transport_and_path",
        lambda url: (fake, "/path"),
    )


def test_git_ls_remote_parses_sha(monkeypatch):
    _patch_dulwich(monkeypatch, refs={b"HEAD": FAKE_SHA.encode()})
    assert _git.ls_remote_head("https://example.com/foo") == FAKE_SHA


def test_git_ls_remote_handles_uppercase_sha(monkeypatch):
    _patch_dulwich(monkeypatch, refs={b"HEAD": FAKE_SHA.upper().encode()})
    assert _git.ls_remote_head("https://example.com/foo") == FAKE_SHA  # lowercased


def test_git_ls_remote_protocol_error_exits_1(monkeypatch):
    _patch_dulwich(monkeypatch, raises=GitProtocolError("repo not found"))
    with pytest.raises(typer.Exit) as exc:
        _git.ls_remote_head("https://example.com/foo")
    assert exc.value.exit_code == 1


def test_git_ls_remote_network_error_exits_1(monkeypatch):
    _patch_dulwich(monkeypatch, raises=OSError("connection refused"))
    with pytest.raises(typer.Exit) as exc:
        _git.ls_remote_head("https://example.com/foo")
    assert exc.value.exit_code == 1


def test_git_ls_remote_missing_head_ref_exits_1(monkeypatch):
    _patch_dulwich(monkeypatch, refs={b"refs/heads/main": FAKE_SHA.encode()})
    with pytest.raises(typer.Exit) as exc:
        _git.ls_remote_head("https://example.com/foo")
    assert exc.value.exit_code == 1


def test_git_ls_remote_invalid_sha_exits_1(monkeypatch):
    _patch_dulwich(monkeypatch, refs={b"HEAD": b"not-a-sha"})
    with pytest.raises(typer.Exit) as exc:
        _git.ls_remote_head("https://example.com/foo")
    assert exc.value.exit_code == 1


def test_git_ls_remote_supports_lsremoteresult_attr(monkeypatch):
    """Both LsRemoteResult.refs and dict-like return values are accepted."""
    plain_dict = {b"HEAD": FAKE_SHA.encode()}

    class _DictClient:
        def get_refs(self, path):
            return plain_dict

    monkeypatch.setattr(_git, "get_transport_and_path", lambda url: (_DictClient(), "/p"))
    assert _git.ls_remote_head("https://example.com/foo") == FAKE_SHA


# ---------- CLI integration ----------


def test_uvx_gh_help_contains_usage_hint():
    result = CliRunner().invoke(cmd, ["--help"])
    assert result.exit_code == 0
    assert "uvx-gh" in result.output or "USER/TOOL" in result.output


def test_uvx_gh_no_args_shows_help(uvx_on_path):
    """Bare `uvx-gh` displays full --help (no_args_is_help) and exits 2."""
    result = CliRunner().invoke(cmd, [])
    assert result.exit_code == 2
    assert "USER/TOOL" in result.output


def test_uvx_gh_user_only_no_tool_spec_exits_1(uvx_on_path, fake_head):
    """`--user X` without tool_spec hits build_uvx_cmd's usage error (exit 1)."""
    result = CliRunner().invoke(cmd, ["--user", "alice"])
    assert result.exit_code == 1


def test_uvx_gh_version_flag_does_not_passthrough():
    result = CliRunner().invoke(cmd, ["--version"])
    assert result.exit_code == 0
    assert "cli version:" in result.output


def test_uvx_gh_version_uses_uvx_gh_module_name():
    result = CliRunner().invoke(cmd, ["--version"], prog_name="uvx-gh")
    assert result.exit_code == 0
    assert result.output.startswith("uvx-gh cli version:")


# ---------- end-to-end: verify `--` reaches ctx.args (R6) ----------


class _ExecCalled(Exception):
    """Marker exception raised by the fake execvp to break out of the callback."""


def _make_fake_execvp(captured: dict):
    def fake_execvp(file: str, args: list) -> None:
        captured["file"] = file
        captured["args"] = list(args)
        raise _ExecCalled()

    return fake_execvp


def test_cli_double_dash_passthrough_reaches_build_uvx_cmd(fake_head, uvx_on_path, monkeypatch):
    captured: dict = {}
    monkeypatch.setattr(os, "execvp", _make_fake_execvp(captured))

    result = CliRunner().invoke(cmd, ["--", "alice/tool", "--user", "bob"])

    assert isinstance(result.exception, _ExecCalled), result.output
    assert captured["file"] == "uvx"
    assert captured["args"] == [
        "uvx",
        "--from",
        f"git+https://github.com/alice/tool@{fake_head}",
        "tool",
        "--user",
        "bob",
    ]


def test_cli_short_path_end_to_end(fake_head, uvx_on_path, monkeypatch):
    captured: dict = {}
    monkeypatch.setattr(os, "execvp", _make_fake_execvp(captured))

    result = CliRunner().invoke(cmd, ["alice/foo@latest", "--port", "8080"])

    assert isinstance(result.exception, _ExecCalled), result.output
    assert captured["args"] == [
        "uvx",
        "--from",
        f"git+https://github.com/alice/foo@{fake_head}",
        "foo",
        "--port",
        "8080",
    ]


def test_cli_user_fallback_end_to_end(fake_head, uvx_on_path, monkeypatch):
    captured: dict = {}
    monkeypatch.setattr(os, "execvp", _make_fake_execvp(captured))

    result = CliRunner().invoke(cmd, ["--user", "alice", "foo"])

    assert isinstance(result.exception, _ExecCalled), result.output
    assert captured["args"] == [
        "uvx",
        "--from",
        f"git+https://github.com/alice/foo@{fake_head}",
        "foo",
    ]


def test_cli_preflight_missing_uvx_exits_127(fake_head, monkeypatch):
    """Pre-flight check fires before build_uvx_cmd; exit 127 with friendly message."""
    import uvx_gh.commands.main as main_mod

    monkeypatch.setattr(main_mod.shutil, "which", lambda name: None)

    result = CliRunner().invoke(cmd, ["alice/foo"])
    assert result.exit_code == 127
    assert "uvx not found on PATH" in result.output
