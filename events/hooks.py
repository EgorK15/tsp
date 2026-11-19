import logging
from contextlib import contextmanager
from contextvars import ContextVar

from pydantic import ValidationError
from sqlalchemy import event

from db.models import Notification
from events.contract import NotificationEvent

logger = logging.getLogger(__name__)

# Идентификатор HTTP-запроса или задачи планировщика, уходит в заголовок x-request-id.
current_request_id = ContextVar("current_request_id", default=None)

PENDING = "pending_notification_events"


@contextmanager
def request_scope(request_id):
    token = current_request_id.set(request_id)
    try:
        yield
    finally:
        current_request_id.reset(token)


def publish_after_commit(session_factory, publisher):
    """Уведомления, созданные в транзакции, уходят в брокер только после её коммита. Возвращает функцию отключения."""

    def collect(session, flush_context):
        for obj in session.new:
            if isinstance(obj, Notification):
                try:
                    session.info.setdefault(PENDING, []).append(NotificationEvent.from_notification(obj))
                except ValidationError as exc:
                    logger.error("notification_id=%s does not match the event contract: %s", obj.id, exc)

    def send(session):
        request_id = current_request_id.get()
        for notification_event in session.info.pop(PENDING, []):
            publisher.publish(notification_event, request_id)

    def drop(session):
        session.info.pop(PENDING, None)

    listeners = [("after_flush", collect), ("after_commit", send), ("after_rollback", drop)]
    for name, listener in listeners:
        event.listen(session_factory, name, listener)

    def remove():
        for name, listener in listeners:
            event.remove(session_factory, name, listener)

    return remove
