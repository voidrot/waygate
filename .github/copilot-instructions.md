# Instructions for WayGate

WayGate is a Python-first monorepo for building Generation-Augmented Retrieval workflows around a shared plugin runtime. The repository currently has three main working areas:

- `apps/` for long-running services such as the web app, scheduler, and workers
- `libs/` for shared runtime, worker, and workflow packages
- `plugins/` for first-party storage, communication, webhook, and provider plugins

The primary operator surface is a server-rendered FastAPI app under `apps/web`, with mountable webhook ingress extracted into `libs/webhooks`.

The repo is not a single app. Changes should respect package boundaries and the plugin-first runtime described in `docs/design/`.

## Global Working Rules

These rules override generic behavior for agents working in this repository.

- State assumptions before writing code or making structural edits.
- Do not claim correctness you have not verified.
- Do not handle only the happy path; check failure modes, edge cases, and rollback behavior.
- Call out security implications when touching webhooks, storage, auth, networking, workflow dispatch, or agent-facing inputs.
- Call out maintainability implications when changing shared contracts, plugin hooks, or package boundaries.
- Prefer surgical changes that follow existing patterns in the touched package instead of introducing a new abstraction layer.
- Derive commands, naming, and conventions from the repository instead of relying on tool defaults or template boilerplate.

## Repo Shape And Boundaries

Use the current repository layout and names when reasoning about changes.

- `apps/web` is the unified FastAPI host for the operator UI, AuthTuna auth flows, and mounted webhook ingress.
- `apps/scheduler` emits scheduled workflow triggers.
- `apps/draft-worker` and `apps/nats-worker` execute workflow triggers over different transports.
- `libs/core` owns bootstrap, plugin hooks, config, logging, and shared schema types.
- `libs/webhooks` owns the mountable FastAPI webhook ingress app and webhook-specific OpenAPI helpers.
- `libs/worker` contains shared worker runtime helpers.
- `libs/workflows` contains workflow logic and LangGraph-based orchestration.
- `plugins/*` contains first-party implementations of the core plugin interfaces.

Do not describe legacy names as current behavior. When architecture questions come up, prefer the terminology used in `docs/design/architecture.md`.

## Backend And Python Workflow

The backend workspace uses Python 3.14+, `uv`, pytest, Ruff, and Pyright-related tooling.

- Prefer `uv` commands for Python environment and package operations.
- Use repo tasks and package-local commands instead of inventing one-off workflows.
- Root setup and test commands should align with the repo files:
  - `uv sync --all-groups --all-extras --all-packages`
  - `uv run pytest`
  - `uv run ruff check . --fix`
  - `uv run ruff format .`
- When touching only one package, run the narrowest relevant tests first.
- When changing shared workflow, plugin, or API contracts, run broader regression coverage before concluding.
- If you could not run validation, say so explicitly and state why.

## Web App

The primary UI now lives in `apps/web` as a server-rendered FastAPI app.

Current web stack:

- FastAPI
- Jinja2 templates
- HTMX
- FastHX for server-rendered page and fragment helpers
- AuthTuna for auth routes and token-oriented auth building blocks
- Tailwind and daisyUI loaded from pinned CDNs unless the user explicitly asks for a local asset pipeline

Web-app working rules:

- Keep page routes, templates, and auth wiring inside `apps/web` unless a cross-app library boundary is clearly justified.
- Put mountable webhook ingress behavior in `libs/webhooks`, not in `libs/core`.
- Preserve the existing Python-first tooling and validation flow; do not introduce a Node build step for the web app unless the user asks for one.
- Keep the parent app's OpenAPI surface authoritative by merging mounted webhook schema into the parent docs.

## Documentation, Design, And Planning

This repository uses markdown documents under `docs/design/` to capture current design decisions and roadmap themes. Those documents are the source of truth for intended architecture and terminology.

- Read `docs/design/` before making structural changes to runtime, workflows, storage, or plugin boundaries.
- Update the relevant design docs when a change materially alters system architecture, contracts, or terminology.
- Use `docs/plans/` for new planning documents and implementation plans.
- Treat `docs/plans/` as historical or proposed context, not the authoritative description of current behavior.
- When code and docs disagree, resolve the mismatch instead of silently following stale text.

## Web App Documentation Expectations

If a change materially affects `apps/web` or `libs/webhooks`, update the relevant documentation instead of leaving the operator surface implicit in backend-only docs.

- Update repo-facing docs when the web app introduces new developer workflows, environment needs, or architectural expectations.
- Keep auth guidance specific to the current AuthTuna integration rather than generic FastAPI auth advice.

## Commit Message Convention

This repository uses [Conventional Commits](https://www.conventionalcommits.org/) to drive automated versioning and changelogs via release-please. All commits must follow this format:

```text
<type>(<scope>): <short summary>
```

Types that trigger a release:

| Type                                                    | Release bump | When to use             |
| ------------------------------------------------------- | ------------ | ----------------------- |
| `feat`                                                  | minor        | New user-facing feature |
| `fix`                                                   | patch        | Bug fix                 |
| `perf`                                                  | patch        | Performance improvement |
| `feat!` / `fix!` / any `!` or `BREAKING CHANGE:` footer | major        | Breaking API change     |

Types that do not trigger a release:

`docs`, `chore`, `refactor`, `test`, `style`, `ci`, `build`

Scope should be the package name or area, for example `core`, `web`, `webhooks`, `local-storage`, or `provider-ollama`.

Examples:

```text
feat(core): add plugin config registration hook
fix(local-storage): handle missing base_path gracefully
feat(web)!: remove deprecated operator endpoint
docs(web): document local operator workflow
chore(release): release waygate-core 0.2.0
```

Agents generating commits or commit message suggestions must follow this convention. Do not use free-form commit messages.

## LangChain And LangGraph

When writing code that uses LangChain or when you need LangChain documentation, always use the `langchain-docs` MCP server defined in `.vscode/mcp.json` to query the official documentation. Do not hardcode API details that can be retrieved from the documentation server.

For workflow changes:

- Keep LangGraph and workflow implementation concerns inside the existing workflow package boundaries unless there is a deliberate architectural reason to move them.
- Do not introduce ad hoc agent-framework patterns without checking the current design docs first.
