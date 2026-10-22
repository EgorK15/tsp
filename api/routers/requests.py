from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response

from api.deps import get_current_user, get_db, get_settings, require_role
from api.routers.categories import get_category_or_404
from api.routers.deals import get_own_deal
from api.schemas.requests import HistoryOut, RequestCreate, RequestOut, RequestUpdate, StageChange
from db import logic
from db.crud import requests

router = APIRouter(prefix="/requests", tags=["requests"])


def request_out(request, settings):
    """Заявка для ответа: добавляет стадию, приоритет сделки и флаги просрочки и возврата."""
    out = RequestOut.model_validate(request)
    out.stage_code = request.stage.code
    out.stage_name = request.stage.name
    out.priority = logic.deal_priority(request.deal)
    out.needs_return = logic.needs_return(request.deal, settings)
    out.is_overdue = logic.is_overdue(request, settings, datetime.now(timezone.utc))
    return out


def history_out(item):
    return HistoryOut(
        id=item.id, from_stage=item.from_stage.code if item.from_stage else None, to_stage=item.to_stage.code,
        changed_by=item.changed_by, changed_at=item.changed_at,
    )


def can_see(request, user):
    if user.role == "head":
        return True
    if user.role == "manager":
        return request.deal.manager_id == user.id
    return any(a.specialist_id == user.id for a in request.assignees)


def get_visible_request(session, request_id, user):
    request = requests.get_request(session, request_id)
    if request is None:
        raise HTTPException(404, "Заявка не найдена")
    if not can_see(request, user):
        raise HTTPException(403, "Нет доступа к заявке")
    return request


@router.get("", response_model=list[RequestOut])
def list_requests(deal_id: int | None = None, stage: str | None = None, session=Depends(get_db),
                  settings=Depends(get_settings), user=Depends(get_current_user)):
    result = requests.list_requests(session, deal_id=deal_id, stage_code=stage)
    return [request_out(r, settings) for r in result if can_see(r, user)]


@router.get("/my", response_model=list[RequestOut])
def my_requests(session=Depends(get_db), settings=Depends(get_settings),
                user=Depends(require_role("specialist"))):
    now = datetime.now(timezone.utc)
    return [request_out(r, settings) for r in requests.my_requests(session, user.id, settings, now)]


@router.post("", response_model=RequestOut, status_code=201)
def create_request(data: RequestCreate, session=Depends(get_db), settings=Depends(get_settings),
                   user=Depends(require_role("manager"))):
    get_own_deal(session, data.deal_id, user)
    get_category_or_404(session, data.category_id)
    request = requests.create_request(session, created_by=user.id, **data.model_dump())
    return request_out(request, settings)


@router.get("/{request_id}", response_model=RequestOut)
def get_request(request_id: int, session=Depends(get_db), settings=Depends(get_settings),
                user=Depends(get_current_user)):
    return request_out(get_visible_request(session, request_id, user), settings)


@router.patch("/{request_id}", response_model=RequestOut)
def update_request(request_id: int, data: RequestUpdate, session=Depends(get_db),
                   settings=Depends(get_settings), user=Depends(get_current_user)):
    get_visible_request(session, request_id, user)
    fields = data.model_dump(exclude_unset=True)
    if user.role == "specialist" and set(fields) - {"result_url"}:
        raise HTTPException(403, "Специалист может менять только ссылку на результат")
    if "category_id" in fields:
        get_category_or_404(session, fields["category_id"])
    return request_out(requests.update_request(session, request_id, **fields), settings)


@router.delete("/{request_id}", status_code=204)
def delete_request(request_id: int, session=Depends(get_db), user=Depends(require_role("manager", "head"))):
    get_visible_request(session, request_id, user)
    requests.delete_request(session, request_id)
    return Response(status_code=204)


@router.post("/{request_id}/stage", response_model=RequestOut)
def change_stage(request_id: int, data: StageChange, session=Depends(get_db), settings=Depends(get_settings),
                 user=Depends(get_current_user)):
    get_visible_request(session, request_id, user)
    return request_out(requests.change_stage(session, request_id, data.to, user), settings)


@router.get("/{request_id}/history", response_model=list[HistoryOut])
def request_history(request_id: int, session=Depends(get_db), user=Depends(get_current_user)):
    get_visible_request(session, request_id, user)
    return [history_out(h) for h in requests.request_history(session, request_id)]
