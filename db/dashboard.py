import statistics
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select

from db import logic
from db.crud import notifications, users
from db.models import LoadSnapshot, Request, Stage


def queue_requests(session):
    query = select(Request).join(Request.stage).where(Stage.kind == "queue").order_by(Request.id)
    return session.scalars(query).all()


def overdue_requests(session, settings, now):
    return [r for r in queue_requests(session) if logic.is_overdue(r, settings, now)]


def median_days_by_priority(session, settings):
    """Медиана рабочих дней от создания заявки до готового КП по приоритетам."""
    days = {1: [], 2: [], 3: []}
    for r in session.scalars(select(Request).where(Request.ready_at.is_not(None))):
        days[logic.deal_priority(r.deal)].append(logic.work_days_between(r.created_at, r.ready_at))
    return {p: statistics.median(values) if values else None for p, values in days.items()}


def ready_without_presentation(session, settings, now):
    query = select(Request).join(Request.stage).where(Stage.code == "ready").order_by(Request.ready_at)
    return [r for r in session.scalars(query) if (now - r.ready_at).days > settings["ready_wait_days"]]


def department_load(session, settings, now):
    result = []
    for user in users.list_users(session, role="specialist"):
        if not user.is_active:
            continue
        load = logic.specialist_load(session, user.id, settings, now)
        result.append((user, load, logic.load_index(load, settings)))
    return result


def take_load_snapshot(session, settings, day):
    """Сохраняет загрузку специалистов на дату (задача Планировщика)."""
    now = datetime.now(timezone.utc)
    snapshots = []
    for user, load, _ in department_load(session, settings, now):
        snapshot = LoadSnapshot(
            snapshot_date=day, specialist_id=user.id, load=Decimal(str(round(load, 2))),
            active_requests=len(logic.active_requests(session, user.id)),
        )
        snapshots.append(session.merge(snapshot))
    session.commit()
    return snapshots


def check_overdue(session, settings, now):
    """Создаёт уведомления исполнителям просроченных заявок."""
    created = []
    for r in overdue_requests(session, settings, now):
        for a in r.assignees:
            created.append(notifications.create_notification(
                session, a.specialist_id, "request_overdue",
                {"request_id": r.id, "title": r.title, "age": logic.request_age(r, now)}, commit=False,
            ))
    session.commit()
    return created
