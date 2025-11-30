# app/db/session.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

db_url = settings.DATABASE_URL

# Timeouts cortos: si la DB no responde → falla rápido (5s)
if db_url.startswith("postgresql+psycopg"):
    # psycopg (async) usa 'connect_timeout' en segundos
    connect_args = {"connect_timeout": 5}
elif db_url.startswith("postgresql+asyncpg"):
    # asyncpg usa 'timeout' (segundos) y podemos fijar UTF-8 en la sesión
    connect_args = {
        "timeout": 5,
        "server_settings": {"client_encoding": "UTF8"},  # 👈 fuerza UTF-8
    }
elif db_url.startswith("sqlite+aiosqlite"):
    connect_args = {}
else:
    connect_args = {}

engine = create_async_engine(
    db_url,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=5,
    max_overflow=10,
    connect_args=connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
