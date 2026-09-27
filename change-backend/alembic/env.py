import os
import sys
from logging.config import fileConfig
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

# 1. Load environment variables from your local .env file
load_dotenv(dotenv_path=backend_dir / ".env")

# This is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

raw_db_url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
if not raw_db_url:
    raise RuntimeError(
        "DATABASE_URL or SUPABASE_DB_URL must be set before running Alembic. "
        "Add it to change-backend/.env or your shell environment."
    )

# Alembic runs migrations synchronously — strip the async driver if present
if "+asyncpg" in raw_db_url:
    db_url = raw_db_url.replace("+asyncpg", "")
elif "+psycopg" in raw_db_url:
    db_url = raw_db_url.replace("+psycopg", "+psycopg2")
else:
    db_url = raw_db_url

config.set_main_option("sqlalchemy.url", db_url)

# 3. Import your Base registry and your explicit models
# This forces Python to read your tables and register them on the metadata clipboard.
from app.database import Base
from app.Users.models import User, UserTier
from app.tasks.models import Task, TaskEvent, TaskEventOutbox, TaskSeries  # noqa: F401
from app.braindump.models import BrainDump
from app.ai.models import AIUsageLog  # noqa: F401
from app.wins.models import Win  # noqa: F401
from app.checkins.models import CheckInType
from app.savings.models import SavingsVault
from app.Users.entitlements_models import FeatureEntitlements

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and getattr(object, "schema", None) == "auth" and name == "users":
        return False
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
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

