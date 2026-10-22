from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RequestCreate(BaseModel):
    deal_id: int
    category_id: int
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None


class RequestUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    result_url: str | None = Field(default=None, max_length=500)
    category_id: int | None = None


class RequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    deal_id: int
    category_id: int
    created_by: int
    title: str
    description: str | None
    result_url: str | None
    created_at: datetime
    stage_changed_at: datetime
    ready_at: datetime | None
    closed_at: datetime | None
    stage_code: str = ""
    stage_name: str = ""
    priority: int = 0
    needs_return: bool = False
    is_overdue: bool = False
