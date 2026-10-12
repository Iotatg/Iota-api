"""IotaDB ORM models: tenants, collections, documents, keys, files, IP list."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class IotaTenant(Base):
    __tablename__ = "iotadb_tenants"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    username: Mapped[str] = mapped_column(String(128), nullable=False, default="sandbox")
    name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    api_calls_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class IotaCollection(Base):
    __tablename__ = "iotadb_collections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_iotadb_coll_user_name"),)


class IotaDocument(Base):
    __tablename__ = "iotadb_documents"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    collection: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[float] = mapped_column(Float, nullable=False)
    updated_at: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (
        Index("ix_iotadb_docs_tenant_coll", "user_id", "collection", "created_at"),
    )


class IotaLiveKey(Base):
    __tablename__ = "iotadb_keys"

    key_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, default="Live Key")
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    key_prefix: Mapped[str] = mapped_column(String(32), nullable=False)
    scopes: Mapped[str] = mapped_column(Text, nullable=False, default='["read","write","storage"]')
    allowed_ips: Mapped[str] = mapped_column(Text, nullable=False, default='["0.0.0.0/0"]')
    created_at: Mapped[float] = mapped_column(Float, nullable=False)
    last_used_at: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class IotaStoredFile(Base):
    __tablename__ = "iotadb_files"

    uid: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mimetype: Mapped[str] = mapped_column(String(128), nullable=False, default="application/octet-stream")
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[float] = mapped_column(Float, nullable=False)


class IotaIpEntry(Base):
    __tablename__ = "iotadb_ip_access"

    entry_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    ip: Mapped[str] = mapped_column(String(64), nullable=False)
    comment: Mapped[str] = mapped_column(String(256), nullable=False, default="Allow access")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    created_at: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "ip", name="uq_iotadb_ip_user"),)
