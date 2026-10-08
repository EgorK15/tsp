from datetime import datetime

from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, ForeignKey, SmallInteger, String, Table, func, text,
)
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
