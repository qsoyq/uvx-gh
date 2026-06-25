# Security Policy

## Supported Versions

Security fixes target the current `main` branch and the latest published package version.

## Reporting a Vulnerability

Do not disclose vulnerabilities in public issues. Report suspected security issues by contacting the repository owner through GitHub.

Include:

- A short description of the issue.
- Affected versions or commits, if known.
- Reproduction steps or a minimal proof of concept.
- Any known workaround.

## Handling

The maintainer will triage the report, determine impact, and publish a fix or advisory when appropriate. Security fixes should keep the change as small as possible and include tests when practical.

## Secret Handling

Never commit tokens, passwords, SSH keys, private certificates, `.env` files, or production configuration. If a secret is committed, rotate it immediately and remove it from history using the appropriate repository procedure.
