from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from db.models import AxisStatus


class DealCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    client_name: str = Field(min_length=1, max_length=255)
    amount: Decimal = Field(default=0, ge=0)
    budget_status: AxisStatus = AxisStatus.none
    timeline_status: AxisStatus = AxisStatus.none
    need_status: AxisStatus = AxisStatus.none
    tz_percent: int = Field(default=0, ge=0, le=100)


class DealUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    client_name: str | None = Field(default=None, min_length=1, max_length=255)
    amount: Decimal | None = Field(default=None, ge=0)
    budget_status: AxisStatus | None = None
    timeline_status: AxisStatus | None = None
    need_status: AxisStatus | None = None
    tz_percent: int | None = Field(default=None, ge=0, le=100)


class DealOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    client_name: str
    manager_id: int
    amount: float
    budget_status: AxisStatus
    timeline_status: AxisStatus
    need_status: AxisStatus
    tz_percent: int
    created_at: datetime
    updated_at: datetime
    priority: int = 0
    needs_return: bool = False
