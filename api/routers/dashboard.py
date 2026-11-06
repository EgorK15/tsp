from datetime import timezone

from fastapi import APIRouter, Depends

from api.deps import get_load_client, get_trace_id, require_role
from api.routers.requests import specialist_load_out
from api.schemas.dashboard import DashboardOut, OverdueOut, ReadyOut, SnapshotOut
from scheduler import jobs

router = APIRouter()


@router.get("/dashboard", response_model=DashboardOut, tags=["dashboard"])
def get_dashboard(user=Depends(require_role("head")), client=Depends(get_load_client),
                  trace_id=Depends(get_trace_id)):
    result = client.get_dashboard(request_id=trace_id)
    return DashboardOut(
        overdue=[
            OverdueOut(id=item.request_id, deal_id=item.deal_id, title=item.title, stage=item.stage,
                       priority=item.priority, age=item.age)
            for item in result.overdue
        ],
        median_days={item.priority: item.days if item.HasField("days") else None for item in result.median_days},
        ready_without_presentation=[
            ReadyOut(id=item.request_id, deal_id=item.deal_id, title=item.title,
                     ready_at=item.ready_at.ToDatetime(tzinfo=timezone.utc), days_waiting=item.days_waiting)
            for item in result.ready_without_presentation
        ],
        load=[specialist_load_out(item) for item in result.load],
    )


@router.post("/scheduler/snapshot", response_model=list[SnapshotOut], tags=["scheduler"])
def take_snapshot(user=Depends(require_role("head")), client=Depends(get_load_client),
                  trace_id=Depends(get_trace_id)):
    return jobs.take_snapshot(client, request_id=trace_id)


@router.post("/scheduler/check-overdue", tags=["scheduler"])
def check_overdue(user=Depends(require_role("head")), client=Depends(get_load_client),
                  trace_id=Depends(get_trace_id)):
    return {"created": jobs.check_overdue(client, request_id=trace_id)}
