from sqlalchemy import select

from db.crud import notifications
from db.models import RequestAssignee, User


def check_specialist(session, user_id):
    user = session.get(User, user_id)
    if user is None or user.role != "specialist":
        raise ValueError(f"Пользователь {user_id} не технический специалист")
    return user


def assign(session, request_id, main_id, co_ids=(), by_user=None):
    """Назначает основного исполнителя и соисполнителей."""
    if by_user is not None and by_user.role != "head":
        raise ValueError("Назначать исполнителей может только руководитель")
    for user_id in [main_id, *co_ids]:
        check_specialist(session, user_id)

    old_main = session.scalar(
        select(RequestAssignee).where(RequestAssignee.request_id == request_id, RequestAssignee.is_main)
    )
    if old_main is not None and old_main.specialist_id != main_id:
        old_main.is_main = False
        session.flush()

    for user_id in [main_id, *co_ids]:
        assignee = session.get(RequestAssignee, (request_id, user_id))
        if assignee is None:
            assignee = RequestAssignee(request_id=request_id, specialist_id=user_id)
            session.add(assignee)
        assignee.is_main = user_id == main_id
        notifications.create_notification(
            session, user_id, "request_assigned",
            {"request_id": request_id, "is_main": user_id == main_id}, commit=False,
        )
    session.commit()
    return list_assignees(session, request_id)


def unassign(session, request_id, specialist_id):
    assignee = session.get(RequestAssignee, (request_id, specialist_id))
    if assignee is None:
        return False
    session.delete(assignee)
    session.commit()
    return True


def list_assignees(session, request_id):
    query = (
        select(RequestAssignee)
        .where(RequestAssignee.request_id == request_id)
        .order_by(RequestAssignee.is_main.desc(), RequestAssignee.specialist_id)
    )
    return session.scalars(query).all()


def reassign_main(session, request_id, new_main_id):
    """Передаёт роль основного исполнителя другому специалисту (при перегрузке)."""
    check_specialist(session, new_main_id)
    old_main = session.scalar(
        select(RequestAssignee).where(RequestAssignee.request_id == request_id, RequestAssignee.is_main)
    )
    if old_main is not None:
        session.delete(old_main)
        session.flush()
    assignee = session.get(RequestAssignee, (request_id, new_main_id))
    if assignee is None:
        assignee = RequestAssignee(request_id=request_id, specialist_id=new_main_id)
        session.add(assignee)
    assignee.is_main = True
    notifications.create_notification(
        session, new_main_id, "request_assigned", {"request_id": request_id, "is_main": True}, commit=False,
    )
    session.commit()
    return assignee
