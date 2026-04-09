# Operator App

The operator app is the first Nuxt-based control plane for WayGate. It hosts the Better Auth backend, keeps auth state in Postgres, and provides the initial authenticated operator UI.

## Environment

Set these variables before running the app:

- `DATABASE_URL`: Postgres connection string for Better Auth tables and sessions.
- `BETTER_AUTH_SECRET`: high-entropy secret used for Better Auth signing and encryption.
- `BETTER_AUTH_URL`: public base URL for the Nuxt app, for example `http://localhost:3000`.
- `RECEIVER_BASE_URL`: base URL for the FastAPI receiver admin API, for example `http://127.0.0.1:8000`.

## Commands

- `pnpm --filter @waygate/operator dev`
- `pnpm --filter @waygate/operator build`
- `pnpm --filter @waygate/operator typecheck`
- `pnpm --filter @waygate/operator auth:migrate`

## Layout

- `lib/auth.ts`: Better Auth server configuration.
- `lib/auth-client.ts`: Vue client for session-aware auth flows.
- `server/utils/receiver-admin.ts`: Better Auth protected proxy helpers for receiver admin requests.
- `server/api/auth/[...all].ts`: Better Auth catch-all route.
- `server/api/receiver/settings/*.ts`: authenticated proxy routes for the receiver settings API.
- `app/pages`: operator pages and auth flows.
