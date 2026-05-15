# uvx-gh

Thin wrapper to `uvx`-run a tool published as a GitHub repo at `github.com/<user>/<tool>[@<ref>]`.

## Install

```bash
# One-off run
uvx uvx-gh alice/foo

# Or install
pip install uvx-gh
# pip install git+https://github.com/qsoyq/uvx-gh.git    # latest from GitHub
```

## Usage

```text
uvx-gh [uvx-options...] USER/TOOL[@REF] [tool-args...]
uvx-gh [uvx-options...] --user USER TOOL[@REF] [tool-args...]
```

The `USER/TOOL` short path takes priority over `--user`. Either is required.

### Ref suffix

| Spec              | Behavior                                                                            |
| ----------------- | ----------------------------------------------------------------------------------- |
| `alice/foo`       | use locally cached HEAD sha; first call resolves via `git ls-remote` and persists   |
| `alice/foo@latest`| force re-resolve HEAD via `git ls-remote` and overwrite the cached sha              |
| `alice/foo@v1.2.3`| pin to git ref (tag / branch / sha) directly — bypasses the sha cache               |

### Extras (PEP 508)

Append `[extras]` to the tool name to request optional dependency groups, just like `pip install pkg[extras]`:

```bash
# httpx CLI requires the [cli] extras (click + pygments + rich) to actually run
uvx-gh encode/httpx[cli] -- https://example.com

# Multiple extras + a pinned ref
uvx-gh "encode/httpx[cli,http2]@master" -- https://example.com
```

Internally this becomes a PEP 508 direct reference forwarded to `uvx`:

```text
uvx --from "httpx[cli] @ git+https://github.com/encode/httpx@<sha>" httpx ...
```

Extras do **not** participate in the sha cache key — the same `<user>/<tool>` shares one ls-remote result across every extras combination, and `@latest` on any variant refreshes the sha for all of them. uv keeps a separate venv per extras combination under `~/.cache/uv/environments-v2/<hash>/`.

> Quote the spec when extras contain commas, otherwise the shell may treat `,` or brackets specially in some contexts.

### `--no-git` (skip the system git binary)

`uv` itself shells out to the system `git` binary when installing a `git+https://` source. On hosts without git (typical Windows boxes that only have `uv` installed), the install fails with `Git executable not found`.

Pass `--no-git` (or set `UVX_GH_NO_GIT=1`) to emit a GitHub archive tarball URL instead — `uv` then downloads over plain HTTP and never calls git:

```bash
uvx-gh --no-git qsoyq/ai-assistant -- --help
# → uvx --from "https://github.com/qsoyq/ai-assistant/archive/<sha>.tar.gz" ai-assistant --help
```

Caveats:
- Public repos only. Private repos still need git credentials.
- `uv` does not reuse a git checkout cache for tarballs, so each new sha re-downloads.

### Why the sha cache?

`uvx --from git+https://...` (without a pinned commit) makes `uv` re-fetch HEAD from GitHub on every call — that's a network roundtrip per invocation. `uvx-gh` resolves HEAD itself via the smart-HTTP `ls-remote` protocol (using dulwich, no system git needed) and pins the URL to the resolved sha (`git+...@<sha>`). After the first run, subsequent calls hit the local cache and incur **zero network traffic** until you explicitly use `@latest`.

Cache location:

- `$UVX_GH_CACHE_HOME` if set
- otherwise `$XDG_CACHE_HOME/uvx-gh/` (default `~/.cache/uvx-gh/`)

Layout: `<cache_dir>/github.com/<user>/<tool>` containing the sha as a single line.

### Pass-through

Anything the wrapper does not recognize is forwarded:

- Tokens before `TOOL_SPEC` go to `uvx` (e.g. `--python 3.12`, `--with extras`)
- Tokens after `TOOL_SPEC` go to the tool itself
- `--` ends wrapper-arg parsing; everything after `--` is treated as tool args

```bash
uvx-gh --python 3.12 alice/foo --port 8080
# → uvx --python 3.12 --from git+https://github.com/alice/foo foo --port 8080

uvx-gh -- alice/foo --user bob
# → uvx --from git+https://github.com/alice/foo foo --user bob
#   (--user bob is forwarded to foo, NOT consumed by uvx-gh)
```

## Requirements

`uvx-gh` depends on the `uv` toolchain (which provides the `uvx` binary). It does **not** require the system `git` CLI — HEAD resolution uses [dulwich](https://github.com/jelmer/dulwich) (pure Python, bundled as a runtime dep).

Install `uv`:

| Platform | Command                                                          |
| -------- | ---------------------------------------------------------------- |
| macOS    | `brew install uv`                                                |
| Linux    | `curl -LsSf https://astral.sh/uv/install.sh \| sh`               |
| Windows  | `winget install --id=astral-sh.uv -e`                            |
| Any      | `pipx install uv`                                                |

`uvx-gh` runs a pre-flight check at startup and exits with a friendly message if `uvx` is not on `PATH`.

## Notes

- On Windows, `os.execvp` is emulated; signal/exit-code semantics differ slightly from POSIX.
- The `UVX_VALUE_FLAGS` whitelist in `uvx_gh/commands/main.py` is hand-synced with `uv`'s value-taking flags. Use `--flag=value` form to bypass the whitelist if a new uv flag is missing.
