# alembic/env.py
from __future__ import annotations

import sys
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import create_engine
from alembic import context

# --- Añade el project root al PYTHONPATH ---
BASE_DIR = Path(__file__).resolve().parents[1]  # repo root
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Importa settings y metadata
from app.core.config import settings
from app.db.base import Base
from app.users.models import User  # asegura registro de modelos

# Carga logging desde alembic.ini (si existe)
config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

# Metadata objetivo para autogenerate
target_metadata = Base.metadata


def _sync_url(url: str) -> str:
    """
    Alembic usa motor SÍNCRONO. Queremos el driver de psycopg3.
    - Si la URL trae +asyncpg -> cámbialo por +psycopg
    - Si ya trae +psycopg -> déjalo
    - Si no trae sufijo -> agrega +psycopg
    """
    if "+asyncpg" in url:
        return url.replace("+asyncpg", "+psycopg")
    if "+psycopg" in url:
        return url
    return url.replace("postgresql://", "postgresql+psycopg://", 1)


def run_migrations_offline():
    """Ejecuta migraciones en modo 'offline'."""
    context.configure(
        url=_sync_url(settings.DATABASE_URL),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Ejecuta migraciones en modo 'online'."""
    sync_url = _sync_url(settings.DATABASE_URL)
    connectable = create_engine(sync_url)  # motor síncrono con psycopg3
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
