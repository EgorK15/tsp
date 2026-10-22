from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    payload: dict
    created_at: datetime
    read_at: datetime | None
