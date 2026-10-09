from datetime import timedelta

from sqlalchemy import select

from db.crud import categories
from db.models import AxisStatus, Request, RequestAssignee, Stage

AXIS_SCORES = {AxisStatus.none: 0, AxisStatus.stated: 1, AxisStatus.confirmed: 2}


def axis_score(status):
    return AXIS_SCORES[status]


def deal_priority(deal):
    """Считает приоритет сделки по трём осям: 4-6 баллов -> 1, 2-3 -> 2, 0-1 -> 3."""
    total = axis_score(deal.budget_status) + axis_score(deal.timeline_status) + axis_score(deal.need_status)
    if total >= 4:
        return 1
    if total >= 2:
        return 2
    return 3


def needs_return(deal, settings):
    """Сделку надо вернуть менеджеру на доработку: низкий приоритет или мало ТЗ."""
    return deal_priority(deal) == 3 or deal.tz_percent < settings["tz_min_percent"]


def work_days_between(start, end):
    days = 0
    day = start.date()
    while day < end.date():
        day += timedelta(days=1)
        if day.weekday() < 5:
            days += 1
    return days


def request_age(request, now):
    return work_days_between(request.created_at, request.closed_at or now)


def is_active(request):
    return request.stage.kind == "queue"


def is_overdue(request, settings, now):
    p = str(deal_priority(request.deal))
    return is_active(request) and request_age(request, now) > settings["norm_days"][p]


def request_weight(request, settings, now):
    p = str(deal_priority(request.deal))
    age = request_age(request, now)
    # вес = вес_приоритета * (1 + min(возраст / норматив, 1))
    return settings["priority_weight"][p] * (1 + min(age / settings["norm_days"][p], 1))


def active_requests(session, specialist_id):
    query = (
        select(Request)
        .join(Request.assignees)
        .join(Request.stage)
        .where(RequestAssignee.specialist_id == specialist_id, Stage.kind == "queue")
        .order_by(Request.id)
    )
    return session.scalars(query).all()


def specialist_load(session, specialist_id, settings, now):
    return sum(request_weight(r, settings, now) for r in active_requests(session, specialist_id))


def load_index(load, settings):
    return load / settings["load_norm"] * 100


def suggest_specialists(session, category_id, settings, now):
    """Специалисты с нужной компетенцией, от наименее загруженного."""
    result = []
    for user in categories.list_specialists_by_category(session, category_id):
        load = specialist_load(session, user.id, settings, now)
        result.append((user, load, load_index(load, settings)))
    result.sort(key=lambda x: x[2])
    return result
