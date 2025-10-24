import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import models  # noqa: F401
from app.config import settings
from app.database import Base


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use sync postgres URL for migrations (psycopg2)
sync_url = settings.sync_database_url.replace("postgresql+asyncpg://", "postgresql://")
config.set_main_option("sqlalchemy.url", sync_url)
target_metadata = Base.metadata


def include_object(object, name, type_, reflected, compare_to):
    """Exclude PostGIS tables from autogenerate."""
    if type_ == "table":
        # Exclude PostGIS tiger and topology tables
        if hasattr(object, "schema") and object.schema in ("tiger", "topology"):
            return False
        # Exclude PostGIS system tables and geocoding tables
        postgis_tables = {
            "spatial_ref_sys", "geocode_settings", "geocode_settings_default",
            "layer", "topology", "tabblock20", "edges", "secondary_unit_lookup",
            "loader_variables", "zcta5", "tabblock", "pagc_rules", "pagc_gaz",
            "state_lookup", "featnames", "faces", "addr", "tract", "place",
            "county", "zip_lookup", "street_type_lookup", "direction_lookup",
            "addrfeat", "zip_lookup_all", "bg", "pagc_lex", "countysub_lookup",
            "loader_lookuptables", "zip_lookup_base", "place_lookup", "zip_state",
            "cousub", "zip_state_loc", "county_lookup", "loader_platform", "state"
        }
        if name in postgis_tables:
            return False
    return True


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=False,  # Changed to False to avoid errors
        dialect_opts={"param style": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        transaction_per_migration=True,  # Use separate transactions per migration
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    # Use sync engine for migrations
    from sqlalchemy import engine_from_config, pool

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

    connectable.dispose()
