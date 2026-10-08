from datetime import datetime, timezone

from sqlalchemy import select

from db import logic
from db.crud import notifications, stages, users
from db.models import Request, RequestAssignee, Stage, StageHistory

TRANSITIONS = {
    "new": ["in_work", "lost"],
    "in_work": ["clarification", "ready", "lost"],
    "clarification": ["in_work", "ready", "lost"],
    "ready": ["presented", "lost"],
    "presented": [],
    "lost": [],
}

ROLE_STAGES = {
    "specialist": ["in_work", "clarification", "ready"],
    "manager": ["presented", "lost"],
}


def create_request(session, deal_id, category_id, title, description, created_by):
    now = datetime.now(timezone.utc)
    stage = stages.get_stage_by_code(session, "new")
    request = Request(
        deal_id=deal_id, category_id=category_id, stage_id=stage.id, created_by=created_by,
        title=title, description=description, created_at=now, stage_changed_at=now,
    )
    session.add(request)
    session.flush()
    session.add(StageHistory(request_id=request.id, to_stage_id=stage.id, changed_by=created_by, changed_at=now))
    for head in users.list_users(session, role="head"):
        notifications.create_notification(
            session, head.id, "request_created",
            {"request_id": request.id, "deal_id": deal_id, "title": title}, commit=False,
        )
    session.commit()
    return request


def get_request(session, request_id):
    return session.get(Request, request_id)


def list_requests(session, deal_id=None, stage_code=None):
    query = select(Request).order_by(Request.id)
    if deal_id:
        query = query.where(Request.deal_id == deal_id)
    if stage_code:
        query = query.join(Request.stage).where(Stage.code == stage_code)
    return session.scalars(query).all()


def update_request(session, request_id, **fields):
    request = get_request(session, request_id)
    if request is None:
        return None
    for key in fields:
        if key not in ("title", "description", "result_url", "category_id"):
            raise ValueError(f"Поле {key} нельзя менять напрямую")
    for key, value in fields.items():
        setattr(request, key, value)
    session.commit()
    return request


def delete_request(session, request_id):
    request = get_request(session, request_id)
    if request is None:
        return False
    session.delete(request)
    session.commit()
    return True


def change_stage(session, request_id, to_code, user):
    """Переводит заявку на другую стадию с проверкой перехода и прав роли."""
    request = get_request(session, request_id)
    if request is None:
        return None
    from_code = request.stage.code
    if to_code not in TRANSITIONS[from_code]:
        raise ValueError(f"Переход {from_code} -> {to_code} недопустим")
    if user.role != "head" and to_code not in ROLE_STAGES[user.role]:
        raise ValueError(f"Роль {user.role} не может переводить заявку в {to_code}")

    now = datetime.now(timezone.utc)
    to_stage = stages.get_stage_by_code(session, to_code)
    session.add(StageHistory(
        request_id=request.id, from_stage_id=request.stage_id, to_stage_id=to_stage.id,
        changed_by=user.id, changed_at=now,
    ))
    request.stage = to_stage
    request.stage_changed_at = now
    if to_code == "ready":
        request.ready_at = now
        notifications.create_notification(
            session, request.deal.manager_id, "request_ready",
            {"request_id": request.id, "title": request.title}, commit=False,
        )
    if to_code in ("presented", "lost"):
        request.closed_at = now
    session.commit()
    return request


def my_requests(session, specialist_id, settings, now):
    """Заявки специалиста: сначала по приоритету сделки, потом самые старые."""
    query = (
        select(Request)
        .join(Request.assignees)
        .where(RequestAssignee.specialist_id == specialist_id, Request.closed_at.is_(None))
    )
    result = session.scalars(query).all()
    return sorted(result, key=lambda r: (logic.deal_priority(r.deal), -logic.request_age(r, now)))


def request_history(session, request_id):
    query = select(StageHistory).where(StageHistory.request_id == request_id).order_by(StageHistory.id)
    return session.scalars(query).all()
