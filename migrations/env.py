from logging.config import fileConfig
from os import getenv
from pathlib import Path
import sys
import tomllib

from alembic import context
from sqlalchemy import engine_from_config
from sqlalchemy import pool

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

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

url = f"postgresql://{getenv('PG_USER', 'postgres')}:{getenv('PG_PASSWORD', 'postgres')}@{getenv('PG_HOST', 'localhost')}:{getenv('PG_PORT', '5432')}/{getenv('PG_DB', 'postgres')}"


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
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
