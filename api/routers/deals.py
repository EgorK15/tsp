from fastapi import APIRouter, Depends, HTTPException, Response

from api.deps import get_db, get_settings, require_role
from api.schemas.deals import DealCreate, DealOut, DealUpdate
from db import logic
from db.crud import deals

router = APIRouter(prefix="/deals", tags=["deals"])


def deal_out(deal, settings):
    """Сделка для ответа: добавляет приоритет и флаг «вернуть менеджеру»."""
    out = DealOut.model_validate(deal)
    out.priority = logic.deal_priority(deal)
    out.needs_return = logic.needs_return(deal, settings)
    return out


def get_own_deal(session, deal_id, user):
    deal = deals.get_deal(session, deal_id)
    if deal is None:
        raise HTTPException(404, "Сделка не найдена")
    if user.role != "head" and deal.manager_id != user.id:
        raise HTTPException(403, "Это чужая сделка")
    return deal


@router.get("", response_model=list[DealOut])
def list_deals(session=Depends(get_db), settings=Depends(get_settings),
               user=Depends(require_role("manager", "head"))):
    manager_id = user.id if user.role == "manager" else None
    return [deal_out(d, settings) for d in deals.list_deals(session, manager_id=manager_id)]


@router.post("", response_model=DealOut, status_code=201)
def create_deal(data: DealCreate, session=Depends(get_db), settings=Depends(get_settings),
                user=Depends(require_role("manager"))):
    deal = deals.create_deal(session, user.id, **data.model_dump())
    return deal_out(deal, settings)


@router.get("/{deal_id}", response_model=DealOut)
def get_deal(deal_id: int, session=Depends(get_db), settings=Depends(get_settings),
             user=Depends(require_role("manager", "head"))):
    return deal_out(get_own_deal(session, deal_id, user), settings)


@router.patch("/{deal_id}", response_model=DealOut)
def update_deal(deal_id: int, data: DealUpdate, session=Depends(get_db), settings=Depends(get_settings),
                user=Depends(require_role("manager", "head"))):
    get_own_deal(session, deal_id, user)
    deal = deals.update_deal(session, deal_id, user.id, **data.model_dump(exclude_unset=True))
    return deal_out(deal, settings)


@router.delete("/{deal_id}", status_code=204)
def delete_deal(deal_id: int, session=Depends(get_db), user=Depends(require_role("manager", "head"))):
    get_own_deal(session, deal_id, user)
    deals.delete_deal(session, deal_id, user.id)
    return Response(status_code=204)
