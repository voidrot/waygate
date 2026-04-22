# Instructions for WayGate

WayGate is a modular platform for building Generation-Augmented Retrieval (GAR) workflows. This repository contains the core framework, libraries, plugins, and MCP server. Users can create their own modules to extend its functionality.

## Global Override Instructions for Agents

These instructions will override any other instructions provided in the repository for GitHub Copilot.

- Do not write code before stating assumptions.
- Do not claim correctness you haven't verified.
- Do not handle only the happy path.
- Under what conditions does this work?
- What are the edge cases?
- What are the security implications?
- What are the maintainability implications?

## Commit Message Convention

This repository uses [Conventional Commits](https://www.conventionalcommits.org/) to drive automated versioning and changelogs via release-please. All commits **must** follow this format:

```
<type>(<scope>): <short summary>
```

**Types that trigger a release:**

| Type                                                    | Release bump | When to use             |
| ------------------------------------------------------- | ------------ | ----------------------- |
| `feat`                                                  | minor        | New user-facing feature |
| `fix`                                                   | patch        | Bug fix                 |
| `perf`                                                  | patch        | Performance improvement |
| `feat!` / `fix!` / any `!` or `BREAKING CHANGE:` footer | major        | Breaking API change     |

**Types that do NOT trigger a release:**

`docs`, `chore`, `refactor`, `test`, `style`, `ci`, `build`

**Scope** should be the package name or area (e.g., `core`, `api`, `local-storage`, `provider-ollama`).

**Examples:**

```
feat(core): add plugin config registration hook
fix(local-storage): handle missing base_path gracefully
feat(api)!: remove deprecated /v1 endpoint
docs(core): update bootstrap usage example
chore(release): release waygate-core 0.2.0
```

Agents generating commits or commit message suggestions must follow this convention. Do not use free-form commit messages.

## Planning and Design

This repository uses markdown files under `docs/design/` to capture current design decisions and future roadmap themes. These documents are the source of truth for how the system works and where it's going. When implementing new features or making changes, refer to these design docs to ensure alignment with the overall architecture and roadmap. Update the design docs as needed when making significant changes or adding new features that impact the system's design.

This repository uses markdown files under `docs/plans/` to capture historical planning documents that informed the current design but are not themselves the source of truth for current behavior. These documents are useful for background and context, but should not be treated as defining current contracts or implementations. When in doubt, refer to the code and the `docs/design/` docs for the current state of the system. When creating a plan always write the plan to a new file under `docs/plans/` rather than editing the existing design docs, to preserve a clear record of how the design evolved over time.

## LangChain

when writing code that uses langchain, or when needing to reference langchain documentation, always use the `langchain-docs` mcp server defined in `.vscode/mcp.json` to query the official langchain documentation. Do not link directly to the documentation or hardcode any information that can be obtained from the documentation, as it may become outdated. Always query the `langchain-docs` mcp server for the most up-to-date information on langchain usage, best practices, and API details.
