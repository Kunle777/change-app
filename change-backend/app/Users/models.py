import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Column, ForeignKey, Table, func
from app.database import Base 


def _ensure_auth_users_reference(metadata) -> None:
    try:
        if any(table.name == "users" and getattr(table, "schema", None) == "auth" for table in metadata.sorted_tables):
            return
    except Exception:
        pass

    Table(
        "users",
        metadata,
        Column("id", UUID(as_uuid=True), primary_key=True),
        schema="auth",
    )


_ensure_auth_users_reference(Base.metadata)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    # remove default=uuid.uuid4 — Supabase Auth generates the ID now, not you
    fcm_token: Mapped[str] = mapped_column(nullable=True)
    phone: Mapped[str] = mapped_column(nullable=True)
    dnd_bypass_enabled: Mapped[bool] = mapped_column(server_default="false", default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    # remove email and password_hash entirely — Supabase Auth owns these now