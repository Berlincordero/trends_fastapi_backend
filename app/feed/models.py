# app/feed/models.py
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    String,
    Integer,
    DateTime,
    func,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.types import UnicodeText
from sqlalchemy.dialects.postgresql import JSONB  # 👈 JSONB para meta de caption
from app.db.base import Base


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # ruta relativa en /media (p.ej. "posts/abc.mp4")
    media_path: Mapped[str] = mapped_column(String(255), nullable=False)

    # Texto “crudo” del caption (para compatibilidad con el front actual)
    caption: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)

    # 👇 Meta estructurada del caption (texto + estilo, incluida la fuente)
    caption_meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    views_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PostStar(Base):
    """
    Reacción ⭐ de un usuario sobre un post.
    Un usuario solo puede reaccionar una vez al mismo post.
    """
    __tablename__ = "post_stars"
    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="uq_post_star"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    post_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("posts.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
