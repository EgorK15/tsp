from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends

from api.deps import get_db, get_settings, require_role
from api.routers.requests import load_out
from api.schemas.dashboard import DashboardOut, OverdueOut, ReadyOut, SnapshotOut
from db import dashboard, logic

router = APIRouter()


@router.get("/dashboard", response_model=DashboardOut, tags=["dashboard"])
def get_dashboard(session=Depends(get_db), settings=Depends(get_settings), user=Depends(require_role("head"))):
    now = datetime.now(timezone.utc)
    overdue = [
        OverdueOut(id=r.id, deal_id=r.deal_id, title=r.title, stage=r.stage.code,
                   priority=logic.deal_priority(r.deal), age=logic.request_age(r, now))
        for r in dashboard.overdue_requests(session, settings, now)
    ]
    ready = [
        ReadyOut(id=r.id, deal_id=r.deal_id, title=r.title, ready_at=r.ready_at,
                 days_waiting=(now - r.ready_at).days)
        for r in dashboard.ready_without_presentation(session, settings, now)
    ]
    return DashboardOut(
        overdue=overdue,
        median_days=dashboard.median_days_by_priority(session, settings),
        ready_without_presentation=ready,
        load=[load_out(*item) for item in dashboard.department_load(session, settings, now)],
    )


@router.post("/scheduler/snapshot", response_model=list[SnapshotOut], tags=["scheduler"])
def take_snapshot(session=Depends(get_db), settings=Depends(get_settings), user=Depends(require_role("head"))):
    return dashboard.take_load_snapshot(session, settings, date.today())


@router.post("/scheduler/check-overdue", tags=["scheduler"])
def check_overdue(session=Depends(get_db), settings=Depends(get_settings), user=Depends(require_role("head"))):
    created = dashboard.check_overdue(session, settings, datetime.now(timezone.utc))
    return {"created": len(created)}
