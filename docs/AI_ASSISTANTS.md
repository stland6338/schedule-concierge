# AI assistants guidance

This document provides neutral guidance for using AI coding assistants (e.g., GitHub Copilot, ChatGPT, Claude) when working in this repository.

Principles:

- AI tools are assistants, not authors. Human maintainers are responsible for all code merged.
- Prefer incremental, well-tested changes. Keep public APIs stable unless required.
- Do not add dependencies or change project structure without clear justification.
- Preserve licenses and avoid copying proprietary content.

Workflow tips:

- Run and update tests when modifying behavior (backend: pytest; frontend: Jest).
- Follow existing patterns: repository + use case + adapter on backend, typed services/components on frontend.
- Keep configuration deterministic in tests; make dev conveniences opt-in.

Security and privacy:

- Do not include secrets in code or logs. Use environment variables.
- Avoid sending sensitive data to external services unless approved.

Attribution:

- Do not list AI assistants as contributors. See `CONTRIBUTORS.md` for human maintainers.
