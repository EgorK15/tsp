from datetime import datetime
from typing import Literal

from pydantic import BaseModel

EXCHANGE = "techqueue.events"
QUEUE = "notifications"
BINDING = "request.*"
DEAD_EXCHANGE = "techqueue.dead"
DEAD_QUEUE = "notifications.dead"
# Обе стороны объявляют очередь с одинаковыми аргументами, иначе брокер откажет с PRECONDITION_FAILED.
QUEUE_ARGUMENTS = {"x-dead-letter-exchange": DEAD_EXCHANGE}

EventType = Literal["request_created", "request_assigned", "request_ready", "request_overdue"]


class NotificationEvent(BaseModel):
    """Событие о новом уведомлении: публикуют API и Scheduler, читает Notification Service."""

    version: Literal[1] = 1
    notification_id: int
    user_id: int
    event_type: EventType
    payload: dict
    created_at: datetime

    @classmethod
    def from_notification(cls, notification):
        return cls(notification_id=notification.id, user_id=notification.user_id,
                   event_type=notification.event_type, payload=notification.payload,
                   created_at=notification.created_at)

    @property
    def routing_key(self):
        return self.event_type.replace("_", ".")
