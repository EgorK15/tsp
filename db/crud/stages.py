from sqlalchemy import select

from db.models import Stage


def create_stage(session, code, name, kind, sort_order):
    stage = Stage(code=code, name=name, kind=kind, sort_order=sort_order)
    session.add(stage)
    session.commit()
    return stage


def get_stage_by_code(session, code):
    return session.scalar(select(Stage).where(Stage.code == code))


def list_stages(session):
    return session.scalars(select(Stage).order_by(Stage.sort_order)).all()
