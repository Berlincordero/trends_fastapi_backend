# app/clips/models.py
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, DateTime, ForeignKey, func

from app.db.base import Base


class Clip(Base):
    __tablename__ = "clips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    # ruta relativa dentro de /media (ej: "clips/xxxx.mp4")
    media_path: Mapped[str] = mapped_column(String(255), nullable=False)

    # id de la canción asociada (opcional)
    music_track_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
