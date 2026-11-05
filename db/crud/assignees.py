from sqlalchemy import select

from db.crud import notifications
from db.models import Request, RequestAssignee, User


def check_specialist(session, user_id, category_id):
    user = session.get(User, user_id)
    if user is None or user.role != "specialist":
        raise ValueError(f"Пользователь {user_id} не технический специалист")
    if not user.is_active or not any(category.id == category_id for category in user.categories):
        raise ValueError(f"Специалист {user_id} неактивен или не имеет нужной компетенции")
    return user


def lock_request(session, request_id):
    return session.scalar(select(Request).where(Request.id == request_id).with_for_update())


def assign(session, request_id, main_id, co_ids=(), by_user=None):
    """Назначает основного исполнителя и соисполнителей."""
    if by_user is not None and by_user.role != "head":
        raise ValueError("Назначать исполнителей может только руководитель")
    request = lock_request(session, request_id)
    if request is None:
        raise ValueError("Заявка не найдена")
    new_ids = dict.fromkeys([main_id, *co_ids])
    for user_id in new_ids:
        check_specialist(session, user_id, request.category_id)

    current = {item.specialist_id: item for item in list_assignees(session, request_id)}
    previous_roles = {user_id: item.is_main for user_id, item in current.items()}
    for user_id, item in current.items():
        if user_id not in new_ids:
            session.delete(item)
        elif item.is_main and user_id != main_id:
            item.is_main = False
    session.flush()

    for user_id in new_ids:
        is_main = user_id == main_id
        assignee = current.get(user_id)
        if assignee is None:
            assignee = RequestAssignee(request_id=request_id, specialist_id=user_id)
            session.add(assignee)
        assignee.is_main = is_main
        if previous_roles.get(user_id) != is_main:
            notifications.create_notification(
                session, user_id, "request_assigned",
                {"request_id": request_id, "is_main": is_main}, commit=False,
            )
    session.commit()
    return list_assignees(session, request_id)


def unassign(session, request_id, specialist_id):
    if lock_request(session, request_id) is None:
        return False
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
    request = lock_request(session, request_id)
    if request is None:
        raise ValueError("Заявка не найдена")
    check_specialist(session, new_main_id, request.category_id)
    old_main = session.scalar(
        select(RequestAssignee).where(RequestAssignee.request_id == request_id, RequestAssignee.is_main)
    )
    if old_main is not None and old_main.specialist_id == new_main_id:
        session.commit()
        return old_main
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
