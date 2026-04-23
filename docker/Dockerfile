# ARG must be declared before the first FROM to be available in all stages.
# Override at build time: docker build --build-arg APP=scheduler ...
ARG APP=web
ARG APP_UID=1000
ARG APP_GID=1000

# =============================================================================
# Stage 1: builder
# Installs all dependencies and bakes workspace packages into the .venv so that
# the runtime stage requires no source files.
# =============================================================================
FROM python:3.14-slim AS builder

# Re-declare ARG to bring it into this stage's scope (Docker scoping rule).
ARG APP

# 1. Install uv from the official distroless image — cleanest and fastest method.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 2. Set optimal uv environment variables.
# Compile bytecode for faster cold starts.
ENV UV_COMPILE_BYTECODE=1
# Copy mode avoids hardlink failures on some Docker storage backends.
ENV UV_LINK_MODE=copy

WORKDIR /app

# --- CACHE LAYER: THIRD-PARTY DEPENDENCIES ---
# Copy ALL workspace member pyproject.toml files and the root lockfile.
# uv needs the full workspace graph to resolve the target app's dependencies,
# even if only --package ${APP} is installed.
# This layer only invalidates when a dependency spec changes — not on source edits.

# 3. Copy root config + lockfile.
COPY pyproject.toml uv.lock ./

# 4. Copy every workspace member's pyproject.toml (preserving directory structure).
COPY apps/web/pyproject.toml        apps/web/
COPY apps/scheduler/pyproject.toml  apps/scheduler/
COPY apps/worker-app/pyproject.toml apps/worker-app/
COPY libs/core/pyproject.toml       libs/core/
COPY libs/webhooks/pyproject.toml   libs/webhooks/
COPY libs/worker/pyproject.toml     libs/worker/
COPY libs/workflows/pyproject.toml  libs/workflows/
COPY plugins/communication-http/pyproject.toml plugins/communication-http/
COPY plugins/communication-nats/pyproject.toml plugins/communication-nats/
COPY plugins/communication-rq/pyproject.toml plugins/communication-rq/
COPY plugins/local-storage/pyproject.toml   plugins/local-storage/
COPY plugins/provider-ollama/pyproject.toml plugins/provider-ollama/
COPY plugins/webhook-agent-session/pyproject.toml plugins/webhook-agent-session/
COPY plugins/webhook-generic/pyproject.toml plugins/webhook-generic/

# 5. Install only the third-party PyPI dependencies for the target app.
# --no-install-workspace: skips local workspace packages (source not copied yet).
# --package waygate-${APP}: uv expects the workspace package name, not folder slug.
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen --no-dev --no-install-workspace --package "waygate-${APP}"

# --- SOURCE LAYER: WORKSPACE CODE ---
# Copies source after the dependency cache layer so that code edits don't bust
# the expensive PyPI install step.

# 6. Copy the target app's source.
COPY apps/${APP}/ apps/${APP}/

# 7. Copy all shared libraries and plugins.
# uv will only install what the target app's dependency graph actually requires.
COPY libs/    libs/
COPY plugins/ plugins/

# 8. Install workspace packages as non-editable.
# --no-editable: installs workspace packages as regular wheels inside .venv
# instead of editable path references. This makes the .venv fully self-contained
# — the runtime stage only needs to copy .venv, not the source tree.
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen --no-dev --no-editable --package "waygate-${APP}"

# =============================================================================
# Stage 1b: migrations
# Installs Alembic tooling plus the first-party core package so migrations can
# run against the repository's root migration config inside Compose.
# =============================================================================
FROM python:3.14-slim AS migrations

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

# Copy the root config, lockfile, and workspace member metadata so uv can
# resolve the workspace consistently before source files are present.
COPY pyproject.toml uv.lock alembic.ini ./
COPY migrations/ migrations/
COPY apps/web/pyproject.toml           apps/web/
COPY apps/scheduler/pyproject.toml     apps/scheduler/
COPY apps/worker-app/pyproject.toml    apps/worker-app/
COPY libs/core/pyproject.toml          libs/core/
COPY libs/webhooks/pyproject.toml      libs/webhooks/
COPY libs/worker/pyproject.toml        libs/worker/
COPY libs/workflows/pyproject.toml     libs/workflows/
COPY plugins/communication-http/pyproject.toml plugins/communication-http/
COPY plugins/communication-nats/pyproject.toml plugins/communication-nats/
COPY plugins/communication-rq/pyproject.toml   plugins/communication-rq/
COPY plugins/local-storage/pyproject.toml      plugins/local-storage/
COPY plugins/provider-ollama/pyproject.toml    plugins/provider-ollama/
COPY plugins/webhook-agent-session/pyproject.toml plugins/webhook-agent-session/
COPY plugins/webhook-generic/pyproject.toml    plugins/webhook-generic/

# Install the root development group, which carries the pinned Alembic runtime.
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen --group dev --no-install-project

# Copy the workspace source tree so Alembic can import first-party packages
# through migrations/env.py when it prepends the member src paths.
COPY apps/ apps/
COPY libs/ libs/
COPY plugins/ plugins/

# Install the first-party core package and preserve the previously installed
# Alembic tooling in the environment.
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen --package waygate-core --no-dev --no-editable --inexact

ENV PATH="/app/.venv/bin:$PATH"

CMD ["alembic", "upgrade", "head"]

# =============================================================================
# Stage 2: runtime
# Clean minimal image containing only the .venv produced by the builder.
# No uv, no build tools, no source files.
# =============================================================================
FROM python:3.14-slim AS runtime

# Re-declare ARG to bring it into this stage's scope.
ARG APP
ARG APP_UID
ARG APP_GID

# 9. Create a non-root user and group to run the application.
# Defaulting to uid/gid 1000 keeps bind-mounted development directories writable
# on typical Linux hosts while still allowing build-time overrides.
RUN addgroup --system --gid "${APP_GID}" appgroup \
  && adduser --system --uid "${APP_UID}" --ingroup appgroup --no-create-home appuser

WORKDIR /app

# 10. Copy only the self-contained virtual environment from the builder stage.
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv

# 11. Persist the build-time APP arg as a runtime environment variable so the
#     CMD shell expansion resolves to the correct entry point script.
ENV APP=${APP}
ENV PATH="/app/.venv/bin:$PATH"

USER appuser

# 12. Invoke the app's entry point script (defined in [project.scripts] in each
#     app's pyproject.toml, e.g. waygate-web or waygate-scheduler).
#     exec replaces the shell process so the application receives OS signals directly.
CMD ["/bin/sh", "-c", "exec waygate-${APP}"]
