from logging.config import fileConfig
from os import getenv
from pathlib import Path
import sys
import tomllib

from alembic import context
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy.engine import URL

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _prepend_workspace_src_paths(repo_root: Path) -> None:
    """Ensure workspace package sources are importable for Alembic.

    The monorepo uses multiple editable packages under the uv workspace. Alembic
    can be executed directly from the repository root before those packages are
    installed into the active environment, so we add every member's `src`
    directory (or package root when it does not use a src layout) to `sys.path`.
    """

    root_pyproject = repo_root / "pyproject.toml"
    if not root_pyproject.exists():
        return

    with root_pyproject.open("rb") as file_handle:
        root_config = tomllib.load(file_handle)

    members = (
        root_config.get("tool", {})
        .get("uv", {})
        .get("workspace", {})
        .get("members", [])
    )
    seen_paths: set[str] = set()

    for member_pattern in members:
        for member_path in sorted(repo_root.glob(member_pattern)):
            if not member_path.is_dir():
                continue

            import_path = member_path / "src"
            resolved_path = import_path if import_path.is_dir() else member_path
            resolved_str = str(resolved_path)
            if resolved_str in seen_paths:
                continue
            seen_paths.add(resolved_str)
            sys.path.insert(0, resolved_str)


repo_root = Path(__file__).resolve().parents[1]
_prepend_workspace_src_paths(repo_root)


def _discover_target_metadata(repo_root: Path):
    from waygate_core.database import discover_migration_metadata

    return discover_migration_metadata(repo_root=repo_root)


# Tell Alembic which SQLAlchemy metadata collections to diff against.
target_metadata = _discover_target_metadata(repo_root)

IGNORED_TABLE_NAMES = {
    "api_key_scopes",
    "api_keys",
    "audit_events",
    "checkpoint_blobs",
    "checkpoint_migrations",
    "checkpoint_writes",
    "checkpoints",
    "deleted_users",
    "encryption_keys",
    "mfa_methods",
    "mfa_recovery_codes",
    "organization",
    "organization_members",
    "passkey_credentials",
    "permissions",
    "role_assign_permissions",
    "role_grant_permissions",
    "role_permissions",
    "roles",
    "sessions",
    "social_accounts",
    "team",
    "team_members",
    "tokens",
    "user_roles",
    "users",
}


def _parent_table_name(object_, type_: str) -> str | None:
    if type_ == "table":
        return getattr(object_, "name", None)

    parent_table = getattr(object_, "table", None)
    if parent_table is not None:
        return getattr(parent_table, "name", None)

    return None


def include_object(object_, name, type_, reflected, compare_to) -> bool:
    del name, reflected, compare_to

    return _parent_table_name(object_, type_) not in IGNORED_TABLE_NAMES


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def _build_database_url() -> str:
    """Build the SQLAlchemy URL used by Alembic.

    The workspace installs `psycopg` v3, so Alembic must request the matching
    SQLAlchemy dialect explicitly instead of relying on the default psycopg2
    driver name.
    """

    def _setting(*names: str, default: str) -> str:
        for name in names:
            value = getenv(name)
            if value is not None and value.strip():
                return value.strip()
        return default

    driver = getenv("PG_DRIVER", "psycopg").strip() or "psycopg"
    return URL.create(
        drivername=f"postgresql+{driver}",
        username=_setting("WAYGATE_CORE__PG_USER", "PG_USER", default="postgres"),
        password=_setting(
            "WAYGATE_CORE__PG_PASSWORD",
            "PG_PASSWORD",
            default="postgres",
        ),
        host=_setting("WAYGATE_CORE__PG_HOST", "PG_HOST", default="localhost"),
        port=int(_setting("WAYGATE_CORE__PG_PORT", "PG_PORT", default="5432")),
        database=_setting("WAYGATE_CORE__PG_DB", "PG_DB", default="postgres"),
    ).render_as_string(hide_password=False)


url = _build_database_url()


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    context.configure(
        url=url,
        target_metadata=target_metadata,
        include_object=include_object,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        {
            "sqlalchemy.url": url,
        },
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
