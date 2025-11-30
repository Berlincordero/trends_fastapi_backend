# app/comments/models.py
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    Integer,
    Text,
    DateTime,
    func,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base import Base


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    post_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("posts.id", ondelete="CASCADE"),
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    # si es respuesta
    parent_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    media: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gift: Mapped[str | None] = mapped_column(String(500), nullable=True)
    style: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ⭐ contador de estrellas (denormalizado)
    stars_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )

    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class CommentStar(Base):
    """
    Quién dio estrella a qué comentario.
    Un usuario solo puede estrellar una vez un comentario.
    """

    __tablename__ = "comment_stars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    comment_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("comments.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "comment_id",
            "user_id",
            name="uq_comment_star_comment_user",
        ),
    )