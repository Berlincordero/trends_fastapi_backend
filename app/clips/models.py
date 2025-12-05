# app/clips/models.py
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, DateTime, ForeignKey, func, UniqueConstraint
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


class ClipView(Base):
    """
    Quién vio qué clip (como los viewers de historias).
    Un usuario cuenta solo una vez por clip.
    """
    __tablename__ = "clip_views"
    __table_args__ = (
      UniqueConstraint("clip_id", "user_id", name="uq_clipview_clip_user"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    clip_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("clips.id", ondelete="CASCADE"),
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )


class ClipStar(Base):
    """
    Quién le dio estrella a qué clip.
    Un usuario solo puede dar 1 estrella por clip.
    """
    __tablename__ = "clip_stars"
    __table_args__ = (
      UniqueConstraint("clip_id", "user_id", name="uq_clipstar_clip_user"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    clip_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("clips.id", ondelete="CASCADE"),
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
