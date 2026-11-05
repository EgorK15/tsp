import logging
from datetime import datetime, timezone
from uuid import uuid4

from db.dashboard import store_load_snapshot, store_overdue_notifications
from db.database import SessionLocal

logger = logging.getLogger(__name__)


def take_snapshot(client, request_id=None, session_factory=SessionLocal):
    """Снимок загрузки отдела: сначала RPC, потом одна транзакция записи на весь снимок."""
    request_id = request_id or uuid4().hex
    day = datetime.now(timezone.utc).date()
    specialists = client.get_department_load(request_id=request_id).specialists
    rows = [(item.specialist_id, item.load, item.active_requests) for item in specialists]
    with session_factory(expire_on_commit=False) as session, session.begin():
        snapshots = store_load_snapshot(session, day, rows)
    logger.info("job=snapshot request_id=%s date=%s rows=%d", request_id, day, len(snapshots))
    return snapshots


def check_overdue(client, request_id=None, session_factory=SessionLocal):
    """Уведомления исполнителям просроченных заявок: сначала RPC, потом одна транзакция на всю пачку."""
    request_id = request_id or uuid4().hex
    overdue = client.get_overdue_requests(request_id=request_id).requests
    rows = [(item.request_id, item.title, item.age, list(item.assignee_ids)) for item in overdue]
    with session_factory.begin() as session:
        created = len(store_overdue_notifications(session, rows))
    logger.info("job=check_overdue request_id=%s overdue=%d created=%d", request_id, len(rows), created)
    return created
