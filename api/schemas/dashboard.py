from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from api.schemas.requests import SpecialistLoadOut


class OverdueOut(BaseModel):
    id: int
    deal_id: int
    title: str
    stage: str
    priority: int
    age: int


class ReadyOut(BaseModel):
    id: int
    deal_id: int
    title: str
    ready_at: datetime
    days_waiting: int


class DashboardOut(BaseModel):
    overdue: list[OverdueOut]
    median_days: dict[int, float | None]
    ready_without_presentation: list[ReadyOut]
    load: list[SpecialistLoadOut]


class SnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    snapshot_date: date
    specialist_id: int
    load: float
    active_requests: int


class SettingIn(BaseModel):
    value: int | float | dict[str, int | float]


class SettingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    value: int | float | dict[str, int | float]
    updated_by: int | None
    updated_at: datetime
