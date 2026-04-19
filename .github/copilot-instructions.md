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
