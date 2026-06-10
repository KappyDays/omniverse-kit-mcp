# Security Policy

## Supported Versions

Security fixes target the current `main` branch.

## Reporting a Vulnerability

Please report security issues privately through GitHub's private vulnerability
reporting for this repository, or contact the maintainer through the GitHub
profile linked from the repository owner account.

Do not include API keys, local `.env` contents, proprietary Kit install paths,
or private scene assets in public issues.

## Local Runtime Notes

This project drives local Kit applications through loopback REST endpoints such
as `http://127.0.0.1:8111`. Treat those endpoints as trusted local developer
interfaces and avoid exposing them to untrusted networks.
