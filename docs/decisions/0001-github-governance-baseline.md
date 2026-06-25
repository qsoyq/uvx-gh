# 0001. GitHub Governance Baseline

## Status

Accepted

## Context

The repository is a public Python CLI package with tests and a PyPI release workflow. It needs a lightweight governance baseline so issues, pull requests, CI checks, security handling, and release approvals are predictable.

## Decision

Adopt a small GitHub Flow baseline:

- Use issues for non-trivial work.
- Use pull requests for all changes to `main`.
- Require the `CI / quality` check before merge.
- Require at least one approving review and CODEOWNERS review.
- Use the `pypi` environment for PyPI publishing.
- Keep release and rollback notes in `docs/release/`.
- Keep major process or architecture decisions in `docs/decisions/`.

## Consequences

Repository changes can define templates, workflows, documentation, and expected settings. Actual branch protection, repository rulesets, secret scanning, Dependabot alerts, and environment reviewers still need GitHub platform configuration or an installed settings automation.
