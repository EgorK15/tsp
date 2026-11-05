from db import dashboard, logic
from db.crud import users
from load_service.calculations import specialist_load_rows
from proto import load_pb2


def department_load(session, settings, now):
    specialists = [user for user in users.list_users(session, role="specialist") if user.is_active]
    return load_pb2.DepartmentLoadResponse(specialists=specialist_load_rows(session, specialists, settings, now))


def overdue_requests(session, settings, now):
    rows = [
        load_pb2.OverdueRequest(
            request_id=request.id,
            deal_id=request.deal_id,
            title=request.title,
            stage=request.stage.code,
            priority=logic.deal_priority(request.deal),
            age=logic.request_age(request, now),
            assignee_ids=[item.specialist_id for item in request.assignees],
        )
        for request in dashboard.overdue_requests(session, settings, now, include_assignees=True)
    ]
    return load_pb2.OverdueRequestsResponse(requests=rows)


def get_dashboard(session, settings, now):
    medians = []
    for priority, days in dashboard.median_days_by_priority(session, settings).items():
        row = load_pb2.MedianDays(priority=priority)
        if days is not None:
            row.days = days
        medians.append(row)

    ready = []
    for request in dashboard.ready_without_presentation(session, settings, now):
        row = load_pb2.ReadyRequest(
            request_id=request.id,
            deal_id=request.deal_id,
            title=request.title,
            days_waiting=(now - request.ready_at).days,
        )
        row.ready_at.FromDatetime(request.ready_at)
        ready.append(row)

    return load_pb2.DashboardResponse(
        overdue=overdue_requests(session, settings, now).requests,
        median_days=medians,
        ready_without_presentation=ready,
        load=department_load(session, settings, now).specialists,
    )
