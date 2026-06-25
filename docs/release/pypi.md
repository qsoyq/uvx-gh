# PyPI Release Process

`uvx-gh` publishes to PyPI through the `Release to PyPI` GitHub Actions workflow.

## Trigger

The workflow runs when:

- A GitHub release is published.
- A maintainer manually dispatches the workflow.

## Pre-Release Checklist

- Confirm the target commit is on `main`.
- Confirm `uv run pre-commit run -a` passes.
- Confirm `uv run pytest` passes.
- Confirm `uv build` passes.
- Confirm `pyproject.toml` contains the intended version.
- Confirm the `pypi` GitHub environment has required reviewers configured.

## Rollback

PyPI files cannot be replaced safely after publication. If a bad package is released:

1. Stop any follow-up automation.
2. Open an incident or release issue.
3. Publish a patch version that restores the previous working behavior or fixes the defect.
4. Document the cause and follow-up prevention in `docs/postmortems/`.

## Platform Follow-Up

The release workflow references the `pypi` environment, but reviewer protection is configured in GitHub, not in workflow YAML. A maintainer should enable required reviewers for the `pypi` environment before treating the release gate as enforced.
