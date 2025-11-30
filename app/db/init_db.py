import logging
from app.db.session import engine
from app.db.base import Base

# 👇 importa todos los modelos que deben existir en la DB
from app.users.models import User
from app.profile.models import Profile
from app.feed.models import Post, PostStar
from app.comments.models import Comment
from app.clips.models import Clip  # 👈 NUEVO

log = logging.getLogger("uvicorn")


async def init_models():
    """
    Crea/verifica todas las tablas declaradas en Base.metadata
    """
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        log.info("✅ DB init: tablas creadas/verificadas.")
    except Exception as e:
        log.error(f"❌ DB init falló: {e!r}")
