# Contributing

Thanks for improving `uvx-gh`. This repository follows a small GitHub Flow process so changes stay reviewable and easy to release.

## Development Flow

1. Open or select an issue before starting non-trivial work.
2. Create a branch from `main` using `<type>/<issue-number>-<short-desc>`, for example `fix/12-cache-error`.
3. Keep the change scoped to the issue. Split unrelated work into separate issues or PRs.
4. Run the local checks before opening a PR.
5. Link the issue from the PR body with `Closes #<issue-number>` when the PR should close it.

## Local Setup

```bash
uv sync --group dev
```

## Checks

Run the same checks expected in CI:

```bash
uv run pre-commit run -a
uv run pytest
uv build
```

## Commit Messages

Use Conventional Commit style:

```text
<type>: <short summary> (#<issue-number>)
```

Common types are `feat`, `fix`, `docs`, `ci`, `chore`, `refactor`, and `test`.

## Pull Requests

Each PR should include:

- A concise summary.
- The linked issue.
- The validation commands and results.
- Known risks and rollback notes.
- Any AI-assisted work that needs reviewer attention.

PRs should target `main` unless a maintainer asks for a different base branch.
