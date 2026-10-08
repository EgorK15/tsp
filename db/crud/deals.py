from sqlalchemy import select

from db.models import AxisStatus, Deal, User


def create_deal(session, manager_id, title, client_name, amount=0,
                budget_status=AxisStatus.none, timeline_status=AxisStatus.none,
                need_status=AxisStatus.none, tz_percent=0):
    deal = Deal(
        manager_id=manager_id, title=title, client_name=client_name, amount=amount,
        budget_status=budget_status, timeline_status=timeline_status,
        need_status=need_status, tz_percent=tz_percent,
    )
    session.add(deal)
    session.commit()
    return deal


def get_deal(session, deal_id):
    return session.get(Deal, deal_id)


def list_deals(session, manager_id=None):
    query = select(Deal).order_by(Deal.id)
    if manager_id:
        query = query.where(Deal.manager_id == manager_id)
    return session.scalars(query).all()


def can_edit(session, deal, user_id):
    user = session.get(User, user_id)
    return user is not None and (user.role == "head" or deal.manager_id == user_id)


def update_deal(session, deal_id, user_id, **fields):
    deal = get_deal(session, deal_id)
    if deal is None:
        return None
    if not can_edit(session, deal, user_id):
        raise ValueError("Редактировать сделку может только её менеджер или руководитель")
    for key, value in fields.items():
        setattr(deal, key, value)
    session.commit()
    return deal


def delete_deal(session, deal_id, user_id):
    deal = get_deal(session, deal_id)
    if deal is None:
        return False
    if not can_edit(session, deal, user_id):
        raise ValueError("Удалить сделку может только её менеджер или руководитель")
    session.delete(deal)
    session.commit()
    return True
