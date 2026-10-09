import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Column, Date, DateTime, Enum, ForeignKey, Index,
    Numeric, SmallInteger, String, Table, Text, func, text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base


specialist_categories = Table(
    "specialist_categories",
    Base.metadata,
    Column("specialist_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", ForeignKey("equipment_categories.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('manager', 'specialist', 'head')", name="ck_users_role"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="manager")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    categories: Mapped[list["EquipmentCategory"]] = relationship(
        secondary=specialist_categories, back_populates="specialists"
    )
    deals: Mapped[list["Deal"]] = relationship(back_populates="manager")

    def __repr__(self):
        return f"<User {self.id} {self.email} {self.role}>"


class EquipmentCategory(Base):
    __tablename__ = "equipment_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)

    specialists: Mapped[list[User]] = relationship(
        secondary=specialist_categories, back_populates="categories"
    )

    def __repr__(self):
        return f"<EquipmentCategory {self.id} {self.name}>"


class Stage(Base):
    __tablename__ = "stages"
    __table_args__ = (
        CheckConstraint("kind IN ('queue', 'ready', 'presented', 'lost')", name="ck_stages_kind"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(20))
    sort_order: Mapped[int] = mapped_column(SmallInteger, default=0)

    def __repr__(self):
        return f"<Stage {self.code}>"


class AxisStatus(enum.Enum):
    none = "none"
    stated = "stated"
    confirmed = "confirmed"


axis_enum = Enum(AxisStatus, name="axis_status")


class Deal(Base):
    __tablename__ = "deals"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_deals_amount"),
        CheckConstraint("tz_percent BETWEEN 0 AND 100", name="ck_deals_tz_percent"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    client_name: Mapped[str] = mapped_column(String(255))
    manager_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    budget_status: Mapped[AxisStatus] = mapped_column(axis_enum, default=AxisStatus.none)
    timeline_status: Mapped[AxisStatus] = mapped_column(axis_enum, default=AxisStatus.none)
    need_status: Mapped[AxisStatus] = mapped_column(axis_enum, default=AxisStatus.none)
    tz_percent: Mapped[int] = mapped_column(SmallInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    manager: Mapped[User] = relationship(back_populates="deals")
    requests: Mapped[list["Request"]] = relationship(
        back_populates="deal", cascade="all, delete-orphan", passive_deletes=True
    )

    def __repr__(self):
        return f"<Deal {self.id} {self.title}>"


class Request(Base):
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("deals.id", ondelete="CASCADE"))
    category_id: Mapped[int] = mapped_column(ForeignKey("equipment_categories.id"))
    stage_id: Mapped[int] = mapped_column(ForeignKey("stages.id"))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    result_url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    stage_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    deal: Mapped[Deal] = relationship(back_populates="requests")
    category: Mapped[EquipmentCategory] = relationship()
    stage: Mapped[Stage] = relationship()
    author: Mapped[User] = relationship()
    assignees: Mapped[list["RequestAssignee"]] = relationship(
        back_populates="request", cascade="all, delete-orphan", passive_deletes=True
    )
    history: Mapped[list["StageHistory"]] = relationship(
        back_populates="request", cascade="all, delete-orphan", passive_deletes=True,
        order_by="StageHistory.changed_at",
    )

    def __repr__(self):
        return f"<Request {self.id} {self.title}>"


class RequestAssignee(Base):
    __tablename__ = "request_assignees"
    __table_args__ = (
        Index("uq_request_main", "request_id", unique=True, postgresql_where=text("is_main")),
    )

    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), primary_key=True)
    specialist_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    is_main: Mapped[bool] = mapped_column(Boolean, default=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    request: Mapped[Request] = relationship(back_populates="assignees")
    specialist: Mapped[User] = relationship()


class StageHistory(Base):
    __tablename__ = "stage_history"
    __table_args__ = (
        Index("ix_stage_history_request", "request_id", "changed_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"))
    from_stage_id: Mapped[int | None] = mapped_column(ForeignKey("stages.id"))
    to_stage_id: Mapped[int] = mapped_column(ForeignKey("stages.id"))
    changed_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    request: Mapped[Request] = relationship(back_populates="history")
    from_stage: Mapped[Stage | None] = relationship(foreign_keys=[from_stage_id])
    to_stage: Mapped[Stage] = relationship(foreign_keys=[to_stage_id])


class LoadSnapshot(Base):
    __tablename__ = "load_snapshots"

    snapshot_date: Mapped[date] = mapped_column(Date, primary_key=True)
    specialist_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    load: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    active_requests: Mapped[int] = mapped_column(default=0)

    specialist: Mapped[User] = relationship()


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    event_type: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship()

    def __repr__(self):
        return f"<Notification {self.id} {self.event_type}>"


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict] = mapped_column(JSONB)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
