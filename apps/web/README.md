# waygate-web

Unified FastAPI application for WayGate.

## Responsibilities

- Hosts the minimal server-rendered control plane with Jinja templates, HTMX fragments, and daisyUI styling
- Initializes AuthTuna for browser and API-oriented auth flows
- Mounts the reusable `waygate-webhooks` ingress sub-application at `/webhooks`
- Merges webhook OpenAPI endpoints into the parent app's docs so the unified app remains the primary surface

## MVP Scope

The current package is an infrastructure-level MVP for the web surface, not a full operator product UI.

Today it provides a small control-plane dashboard, mounted auth flows, mounted webhook ingress, and a unified OpenAPI surface. Document browsing, review workflows, retrieval surfaces, and broader operator tooling remain outside this package's current scope.

## Running

```bash
uv run waygate-web
```

## Auth Configuration

The app seeds local-development AuthTuna settings when auth environment variables are absent. These defaults are intended only for local development and should be overridden in deployed environments.

The web package now uses typed `pydantic-settings` models for both auth and non-auth runtime configuration.

- `WaygateWebAuthSettings` controls the AuthTuna surface.
- `WaygateWebRuntimeSettings` controls the package's non-auth runtime settings such as bind host, port, and app metadata.

The auth configuration initializes AuthTuna with `dont_use_env=True`. That means bare AuthTuna env vars such as `JWT_SECRET_KEY` or `API_BASE_URL` are ignored by the web app. Use only `WAYGATE_WEB_AUTH__...` variables.

### WayGate Default Overrides

The wrapper preserves AuthTuna defaults unless noted here.

| Setting                | WayGate default                  | AuthTuna default  |
| ---------------------- | -------------------------------- | ----------------- |
| `APP_NAME`             | `WayGate`                        | `AuthTuna`        |
| `API_BASE_URL`         | `http://localhost:8080`          | required upstream |
| `FERNET_KEYS`          | one local-development Fernet key | empty list        |
| `SESSION_SECURE`       | `false`                          | `true`            |
| `UI_ENABLED`           | `true`                           | upstream-defined  |
| `ADMIN_ROUTES_ENABLED` | `false`                          | upstream-defined  |

The web package now owns the AuthTuna-facing templates that operators actually see:

- Auth pages live under `waygate_web/templates/authtuna/auth`.
- User and organization pages live under `waygate_web/templates/authtuna/user`.
- Email templates live under `waygate_web/templates/authtuna/email`.
- Package-relative template defaults are resolved to real filesystem paths in code before AuthTuna initializes, so local development does not need absolute template paths.

This keeps AuthTuna's existing handlers and JSON endpoints in place while letting WayGate control the rendered look and feel.

### Value Encoding

- Scalar values use normal `.env` strings, for example `WAYGATE_WEB_AUTH__APP_NAME = "WayGate"`.
- List values must be JSON arrays, for example `WAYGATE_WEB_AUTH__FINGERPRINT_HEADERS = '["User-Agent", "Accept-Language"]'`.
- Secret values are still plain strings in `.env` files and should be provided by the deployment environment in production.
- Nested theme settings use the same delimiter as the rest of the settings surface, for example `WAYGATE_WEB_AUTH__THEME__LIGHT__PRIMARY`.
- The root [env.example](/home/buck/src/voidrot/waygate/env.example) and [env.compose.example](/home/buck/src/voidrot/waygate/env.compose.example) files include commented examples for every supported auth setting.

### AuthTuna Reference Surface

#### Application

- `WAYGATE_WEB_AUTH__APP_NAME`
- `WAYGATE_WEB_AUTH__ALGORITHM`
- `WAYGATE_WEB_AUTH__API_BASE_URL`
- `WAYGATE_WEB_AUTH__TRY_FULL_INITIALIZE_WHEN_SYSTEM_USER_EXISTS_AGAIN`

#### Security

- `WAYGATE_WEB_AUTH__JWT_SECRET_KEY`
- `WAYGATE_WEB_AUTH__ENCRYPTION_PRIMARY_KEY`
- `WAYGATE_WEB_AUTH__ENCRYPTION_SECONDARY_KEYS`
- `WAYGATE_WEB_AUTH__FERNET_KEYS`

#### Feature Flags

- `WAYGATE_WEB_AUTH__MFA_ENABLED`
- `WAYGATE_WEB_AUTH__PASSKEYS_ENABLED`
- `WAYGATE_WEB_AUTH__UI_ENABLED`
- `WAYGATE_WEB_AUTH__ADMIN_ROUTES_ENABLED`
- `WAYGATE_WEB_AUTH__PASSWORDLESS_LOGIN_ENABLED`
- `WAYGATE_WEB_AUTH__ONLY_MIDDLEWARE`

#### Default Users And Roles

- `WAYGATE_WEB_AUTH__DEFAULT_SUPERADMIN_PASSWORD`
- `WAYGATE_WEB_AUTH__DEFAULT_ADMIN_PASSWORD`
- `WAYGATE_WEB_AUTH__DEFAULT_SUPERADMIN_EMAIL`
- `WAYGATE_WEB_AUTH__DEFAULT_ADMIN_EMAIL`

#### Database

- `WAYGATE_WEB_AUTH__DEFAULT_DATABASE_URI`
- `WAYGATE_WEB_AUTH__DATABASE_USE_ASYNC_ENGINE`
- `WAYGATE_WEB_AUTH__AUTO_CREATE_DATABASE`
- `WAYGATE_WEB_AUTH__DATABASE_POOL_SIZE`
- `WAYGATE_WEB_AUTH__DATABASE_MAX_OVERFLOW`
- `WAYGATE_WEB_AUTH__DATABASE_POOL_TIMEOUT`
- `WAYGATE_WEB_AUTH__DATABASE_POOL_RECYCLE`
- `WAYGATE_WEB_AUTH__DATABASE_POOL_PRE_PING`

When `WAYGATE_WEB_AUTH__AUTO_CREATE_DATABASE` is enabled, the web app now performs AuthTuna table creation during FastAPI startup instead of waiting for the first request that touches `db_manager.get_db()`.

#### Session

- `WAYGATE_WEB_AUTH__FINGERPRINT_HEADERS`
- `WAYGATE_WEB_AUTH__SESSION_DB_VERIFICATION_INTERVAL`
- `WAYGATE_WEB_AUTH__SESSION_LIFETIME_SECONDS`
- `WAYGATE_WEB_AUTH__SESSION_ABSOLUTE_LIFETIME_SECONDS`
- `WAYGATE_WEB_AUTH__SESSION_LIFETIME_FROM`
- `WAYGATE_WEB_AUTH__SESSION_SAME_SITE`
- `WAYGATE_WEB_AUTH__SESSION_SECURE`
- `WAYGATE_WEB_AUTH__SESSION_TOKEN_NAME`
- `WAYGATE_WEB_AUTH__SESSION_COOKIE_DOMAIN`
- `WAYGATE_WEB_AUTH__LOCK_SESSION_REGION`
- `WAYGATE_WEB_AUTH__DISABLE_RANDOM_STRING`
- `WAYGATE_WEB_AUTH__RANDOM_STRING_GRACE`

#### Email, PII, And Token Delivery

- `WAYGATE_WEB_AUTH__EMAIL_ENABLED`
- `WAYGATE_WEB_AUTH__SMTP_HOST`
- `WAYGATE_WEB_AUTH__SMTP_PORT`
- `WAYGATE_WEB_AUTH__SMTP_USERNAME`
- `WAYGATE_WEB_AUTH__SMTP_PASSWORD`
- `WAYGATE_WEB_AUTH__DKIM_PRIVATE_KEY_PATH`
- `WAYGATE_WEB_AUTH__DKIM_DOMAIN`
- `WAYGATE_WEB_AUTH__DKIM_SELECTOR`
- `WAYGATE_WEB_AUTH__DEFAULT_SENDER_EMAIL`
- `WAYGATE_WEB_AUTH__EMAIL_DOMAINS`
- `WAYGATE_WEB_AUTH__PII_ENCRYPTION_ENABLED`
- `WAYGATE_WEB_AUTH__PII_HMAC_KEY`
- `WAYGATE_WEB_AUTH__ENCRYPT_AUDIT_IP`
- `WAYGATE_WEB_AUTH__TOKENS_EXPIRY_SECONDS`
- `WAYGATE_WEB_AUTH__TOKENS_MAX_COUNT_PER_DAY_PER_USER_PER_ACTION`
- `WAYGATE_WEB_AUTH__MAIL_STARTTLS`
- `WAYGATE_WEB_AUTH__MAIL_SSL_TLS`
- `WAYGATE_WEB_AUTH__USE_CREDENTIALS`
- `WAYGATE_WEB_AUTH__VALIDATE_CERTS`

#### Templates

- `WAYGATE_WEB_AUTH__EMAIL_TEMPLATE_DIR`
- `WAYGATE_WEB_AUTH__HTML_TEMPLATE_DIR`
- `WAYGATE_WEB_AUTH__DASHBOARD_AND_USER_INFO_PAGES_TEMPLATE_DIR`

#### OAuth

- `WAYGATE_WEB_AUTH__GOOGLE_CLIENT_ID`
- `WAYGATE_WEB_AUTH__GOOGLE_CLIENT_SECRET`
- `WAYGATE_WEB_AUTH__GOOGLE_REDIRECT_URI`
- `WAYGATE_WEB_AUTH__GITHUB_CLIENT_ID`
- `WAYGATE_WEB_AUTH__GITHUB_CLIENT_SECRET`
- `WAYGATE_WEB_AUTH__GITHUB_REDIRECT_URI`

#### RPC

- `WAYGATE_WEB_AUTH__RPC_ENABLED`
- `WAYGATE_WEB_AUTH__RPC_AUTOSTART`
- `WAYGATE_WEB_AUTH__RPC_TOKEN`
- `WAYGATE_WEB_AUTH__RPC_TLS_CERT_FILE`
- `WAYGATE_WEB_AUTH__RPC_TLS_KEY_FILE`
- `WAYGATE_WEB_AUTH__RPC_ADDRESS`

#### WebAuthn

- `WAYGATE_WEB_AUTH__WEBAUTHN_ENABLED`
- `WAYGATE_WEB_AUTH__WEBAUTHN_RP_ID`
- `WAYGATE_WEB_AUTH__WEBAUTHN_RP_NAME`
- `WAYGATE_WEB_AUTH__WEBAUTHN_ORIGIN`

#### Authentication Strategy

- `WAYGATE_WEB_AUTH__STRATEGY`

#### API Keys

- `WAYGATE_WEB_AUTH__API_KEY_PREFIX_SECRET`
- `WAYGATE_WEB_AUTH__API_KEY_PREFIX_PUBLISHABLE`
- `WAYGATE_WEB_AUTH__API_KEY_PREFIX_MASTER`
- `WAYGATE_WEB_AUTH__API_KEY_PREFIX_OTHER`
- `WAYGATE_WEB_AUTH__MAX_MASTER_KEYS_PER_USER`
- `WAYGATE_WEB_AUTH__MAX_API_KEYS_PER_USER`
- `WAYGATE_WEB_AUTH__MAX_SCOPES_PER_SECRET_KEY`
- `WAYGATE_WEB_AUTH__KEY_HASH_ALGORITHM`

#### Login Rate Limiting

- `WAYGATE_WEB_AUTH__MAX_LOGIN_ATTEMPTS_PER_IP`
- `WAYGATE_WEB_AUTH__MAX_LOGIN_ATTEMPTS_PER_USER`
- `WAYGATE_WEB_AUTH__LOGIN_RATE_LIMIT_WINDOW_SECONDS`
- `WAYGATE_WEB_AUTH__LOGIN_LOCKOUT_DURATION_SECONDS`

#### Theme

AuthTuna's theme object can be overridden programmatically, but the full nested env surface is available when you need it.

- `WAYGATE_WEB_AUTH__THEME__MODE`
- `WAYGATE_WEB_AUTH__THEME__LIGHT__BACKGROUND_START`
- `WAYGATE_WEB_AUTH__THEME__LIGHT__BACKGROUND_END`
- `WAYGATE_WEB_AUTH__THEME__LIGHT__FOREGROUND`
- `WAYGATE_WEB_AUTH__THEME__LIGHT__MUTED_FOREGROUND`
- `WAYGATE_WEB_AUTH__THEME__LIGHT__CARD`
- `WAYGATE_WEB_AUTH__THEME__LIGHT__CARD_FOREGROUND`
- `WAYGATE_WEB_AUTH__THEME__LIGHT__POPOVER`
- `WAYGATE_WEB_AUTH__THEME__LIGHT__POPOVER_FOREGROUND`
- `WAYGATE_WEB_AUTH__THEME__LIGHT__PRIMARY`
- `WAYGATE_WEB_AUTH__THEME__LIGHT__PRIMARY_FOREGROUND`
- `WAYGATE_WEB_AUTH__THEME__LIGHT__SECONDARY`
- `WAYGATE_WEB_AUTH__THEME__LIGHT__SECONDARY_FOREGROUND`
- `WAYGATE_WEB_AUTH__THEME__LIGHT__MUTED`
- `WAYGATE_WEB_AUTH__THEME__LIGHT__ACCENT`
- `WAYGATE_WEB_AUTH__THEME__LIGHT__ACCENT_FOREGROUND`
- `WAYGATE_WEB_AUTH__THEME__LIGHT__DESTRUCTIVE`
- `WAYGATE_WEB_AUTH__THEME__LIGHT__DESTRUCTIVE_FOREGROUND`
- `WAYGATE_WEB_AUTH__THEME__LIGHT__BORDER`
- `WAYGATE_WEB_AUTH__THEME__LIGHT__INPUT`
- `WAYGATE_WEB_AUTH__THEME__LIGHT__RING`
- `WAYGATE_WEB_AUTH__THEME__DARK__BACKGROUND_START`
- `WAYGATE_WEB_AUTH__THEME__DARK__BACKGROUND_END`
- `WAYGATE_WEB_AUTH__THEME__DARK__FOREGROUND`
- `WAYGATE_WEB_AUTH__THEME__DARK__MUTED_FOREGROUND`
- `WAYGATE_WEB_AUTH__THEME__DARK__CARD`
- `WAYGATE_WEB_AUTH__THEME__DARK__CARD_FOREGROUND`
- `WAYGATE_WEB_AUTH__THEME__DARK__POPOVER`
- `WAYGATE_WEB_AUTH__THEME__DARK__POPOVER_FOREGROUND`
- `WAYGATE_WEB_AUTH__THEME__DARK__PRIMARY`
- `WAYGATE_WEB_AUTH__THEME__DARK__PRIMARY_FOREGROUND`
- `WAYGATE_WEB_AUTH__THEME__DARK__SECONDARY`
- `WAYGATE_WEB_AUTH__THEME__DARK__SECONDARY_FOREGROUND`
- `WAYGATE_WEB_AUTH__THEME__DARK__MUTED`
- `WAYGATE_WEB_AUTH__THEME__DARK__ACCENT`
- `WAYGATE_WEB_AUTH__THEME__DARK__ACCENT_FOREGROUND`
- `WAYGATE_WEB_AUTH__THEME__DARK__DESTRUCTIVE`
- `WAYGATE_WEB_AUTH__THEME__DARK__DESTRUCTIVE_FOREGROUND`
- `WAYGATE_WEB_AUTH__THEME__DARK__BORDER`
- `WAYGATE_WEB_AUTH__THEME__DARK__INPUT`
- `WAYGATE_WEB_AUTH__THEME__DARK__RING`

Legacy compatibility aliases for older ad hoc auth env names have been removed. Use only the canonical `WAYGATE_WEB_AUTH__...` variables.

The canonical non-auth runtime env surface is under the `WAYGATE_WEB__` prefix. Examples:

- `WAYGATE_WEB__HOST`
- `WAYGATE_WEB__PORT`
- `WAYGATE_WEB__TITLE`
- `WAYGATE_WEB__DESCRIPTION`
- `WAYGATE_WEB__VERSION`

Unprefixed process env vars such as `HOST` and `PORT` are no longer used by the web package.
