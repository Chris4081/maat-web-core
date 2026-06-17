# Security Policy

## Supported Versions

MAAT Web Core is an early public project. Security fixes should target the current `main` branch unless release branches are introduced later.

## Reporting a Vulnerability

Please do not publish security-sensitive details in a public issue before the project maintainer has had time to respond.

Preferred reporting path:

1. Open a GitHub security advisory if the repository has private vulnerability reporting enabled.
2. If private reporting is not available yet, open a minimal public issue without exploit details and ask for a private contact path.
3. Include the affected version or commit, platform, configuration, reproduction steps, and impact.

Project page: <https://www.maat-research.com>

## Scope

Relevant security topics include:

- Authentication or session bypass
- Remote code execution
- Unsafe file creation, deletion, or path traversal
- Prompt/context leaks that expose private local data
- Model/API adapter behavior that sends local data to an unexpected external endpoint
- Unsafe handling of attachments, generated files, logs, or memories

## Local-First Assumption

MAAT Web Core is designed as a local tool. If you expose it to a LAN or the internet, enable authentication, use a firewall, and carefully review model/API endpoints.

## Sensitive Data

Do not include private chatlogs, memories, documents, model files, tokens, passwords, or personal data in bug reports.

## Disclaimer

This project is provided under the GNU AGPL v3.0 without warranty. Generated outputs and model behavior must be reviewed by users before being trusted in sensitive contexts.
