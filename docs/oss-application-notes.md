# Codex for OSS Application Notes

This page keeps public, non-personal project facts that are useful when applying
for open-source support programs such as Codex for OSS.

## Project

- **Name**: omniverse-kit-mcp
- **Repository**: https://github.com/KappyDays/omniverse-kit-mcp
- **License**: MIT
- **Primary language**: Python
- **Runtime target**: Windows, NVIDIA Isaac Sim 5.1, USD Composer, MCP clients

## Short Description

omniverse-kit-mcp is an MCP server and Omniverse Kit Extension that lets agentic
coding tools drive NVIDIA Isaac Sim and USD Composer through structured tools
instead of ad hoc GUI automation. It exposes stage editing, simulation control,
robot and character workflows, sensors, physics, lighting, materials, synthetic
data generation, OmniGraph, content browsing, extension management, and
reproducible scenario execution as MCP tools and resources.

## Why This Fits Codex for OSS

The project turns a local robotics and simulation workstation into a testable
MCP surface. Codex can inspect the repository, edit the server and extension,
run the mock-based pytest suite, regenerate the tool catalog, and help maintain
the rule-heavy documentation that keeps live Omniverse workflows reproducible.

Support would directly improve:

- MCP tool coverage for Isaac Sim and USD Composer workflows.
- Regression tests around tool registration, generated catalogs, and scenarios.
- Documentation that helps other developers wire Codex or Claude Code into a
  local Omniverse Kit app safely.
- Public examples for agent-driven robotics, simulation, SDG, and USD scene
  manipulation.

## Maintenance Signals

- 133 MCP tools and 5 on-demand MCP resources are documented in
  `docs/tool-catalog.md`.
- The test suite is mock-based and can run without launching Isaac Sim.
- Generated local research artifacts, screenshots, runtime state, and secrets
  are ignored so public clones stay lightweight.
- The repository includes `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`, and
  explicit public repo hygiene notes.

## Public Boundary

The public repository should contain source code, tests, scenario YAML, setup
scripts, and curated project documentation. It should not publish local
generated extension catalogs, copied reference snapshots, workshop screenshots,
`.env`, virtual environments, live validation artifacts, or machine-specific
runtime output.

Before making the existing private repository public, either rewrite history to
remove prior local/generated artifacts or publish from a clean public snapshot.
The current tree is prepared for public use, but old git history may still
contain files that were intentionally removed from the public-ready state.

## Form Draft

The application form currently asks for personal identity fields, GitHub
identity, a public repository URL, maintainer role, why the repository fits the
program, OpenAI organization ID, planned API credit use, and optional additional
context. Keep personal fields out of this repository.

Known public fields:

- **GitHub username**: KappyDays
- **GitHub repository URL**: https://github.com/KappyDays/omniverse-kit-mcp
- **Role**: Primary maintainer, if this matches the submitter's GitHub role.

Suggested answer for "Why is this repository a good fit?":

> omniverse-kit-mcp gives Codex and other MCP clients a structured bridge into
> NVIDIA Isaac Sim and USD Composer. It exposes 133 tools plus 5 resources for
> robotics, simulation, USD scene work, SDG, sensors, physics, and reproducible
> scenarios. The project is MIT-licensed, actively tested, and aims to make
> agent-driven simulation workflows maintainable for the wider MCP ecosystem.

Suggested answer for "How will you use API credits?":

> API credits would support Codex-assisted maintenance: reviewing pull requests,
> triaging issues, expanding MCP tool coverage, generating and validating
> scenario tests, improving security review, and keeping the generated tool
> catalog and public documentation in sync with Isaac Sim and USD Composer
> changes.

Suggested optional context:

> The repository has been cleaned for public release: generated catalogs,
> copied reference snapshots, screenshots, runtime state, and secrets are
> ignored or removed from the current tree. The remaining open question is
> whether to publish from a clean snapshot or rewrite old private history before
> switching the existing repository to public.
