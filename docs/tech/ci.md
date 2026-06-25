# CI Quality Gate

The `CI` workflow runs on pull requests and pushes to `main`.

## Required Check

The required status check name is:

```text
CI / quality
```

Use this exact name when configuring branch protection or repository rulesets.

## Steps

The workflow:

1. Installs the project with the development dependency group.
2. Runs all pre-commit hooks.
3. Runs the pytest suite.
4. Builds the package.

## Local Equivalent

```bash
uv sync --group dev
uv run pre-commit run -a
uv run pytest
uv build
```

## Platform Follow-Up

GitHub branch protection or a repository ruleset should require `CI / quality` before merge. The repository contains `.github/settings.yml` as the expected configuration, but that file only takes effect when an appropriate settings automation is installed and applied.
