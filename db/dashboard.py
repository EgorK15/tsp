import statistics
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import contains_eager, joinedload, selectinload

from db import logic
from db.crud import notifications, users
from db.models import LoadSnapshot, Request, Stage


def queue_requests(session, include_assignees=False):
    query = (
        select(Request).join(Request.stage)
        .options(contains_eager(Request.stage), joinedload(Request.deal))
        .where(Stage.kind == "queue").order_by(Request.id)
    )
    if include_assignees:
        query = query.options(selectinload(Request.assignees))
    return session.scalars(query).all()


def overdue_requests(session, settings, now, include_assignees=False):
    return [r for r in queue_requests(session, include_assignees) if logic.is_overdue(r, settings, now)]


def median_days_by_priority(session, settings):
    """Медиана рабочих дней от создания заявки до готового КП по приоритетам."""
    days = {1: [], 2: [], 3: []}
    query = select(Request).options(joinedload(Request.deal)).where(Request.ready_at.is_not(None))
    for r in session.scalars(query):
        days[logic.deal_priority(r.deal)].append(logic.work_days_between(r.created_at, r.ready_at))
    return {p: statistics.median(values) if values else None for p, values in days.items()}


def ready_without_presentation(session, settings, now):
    query = (
        select(Request).join(Request.stage)
        .where(Stage.code == "ready", Request.ready_at.is_not(None)).order_by(Request.ready_at)
    )
    return [r for r in session.scalars(query) if (now - r.ready_at).days > settings["ready_wait_days"]]


def department_load(session, settings, now):
    result = []
    for user in users.list_users(session, role="specialist"):
        if not user.is_active:
            continue
        load = logic.specialist_load(session, user.id, settings, now)
        result.append((user, load, logic.load_index(load, settings)))
    return result


def store_load_snapshot(session, day, rows):
    """Записывает строки (специалист, загрузка, число заявок) в транзакции вызывающего."""
    values = [
        dict(snapshot_date=day, specialist_id=user_id, load=Decimal(str(round(load, 2))),
             active_requests=count)
        for user_id, load, count in sorted(rows)
    ]
    if not values:
        return []
    statement = insert(LoadSnapshot).values(values)
    statement = statement.on_conflict_do_update(
        index_elements=[LoadSnapshot.snapshot_date, LoadSnapshot.specialist_id],
        set_={"load": statement.excluded.load, "active_requests": statement.excluded.active_requests},
    ).returning(LoadSnapshot)
    snapshots = session.scalars(statement, execution_options={"populate_existing": True}).all()
    return sorted(snapshots, key=lambda item: item.specialist_id)


def take_load_snapshot(session, settings, day):
    """Сохраняет загрузку специалистов на дату (задача Планировщика)."""
    now = datetime.now(timezone.utc)
    specialists = [user for user in users.list_users(session, role="specialist") if user.is_active]
    loads = logic.specialist_loads(session, [user.id for user in specialists], settings, now)
    snapshots = store_load_snapshot(
        session, day, ((user_id, load, count) for user_id, (load, count) in loads.items()),
    )
    session.commit()
    return snapshots


def store_overdue_notifications(session, rows):
    """Сохраняет строки (заявка, название, возраст, исполнители) в транзакции вызывающего."""
    return [
        notifications.create_notification(
            session, user_id, "request_overdue",
            {"request_id": request_id, "title": title, "age": age}, commit=False,
        )
        for request_id, title, age, assignee_ids in rows
        for user_id in assignee_ids
    ]


def check_overdue(session, settings, now):
    """Создаёт уведомления исполнителям просроченных заявок."""
    rows = (
        (r.id, r.title, logic.request_age(r, now), [a.specialist_id for a in r.assignees])
        for r in overdue_requests(session, settings, now, include_assignees=True)
    )
    created = store_overdue_notifications(session, rows)
    session.commit()
    return created
