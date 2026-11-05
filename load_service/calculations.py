from db import logic
from db.crud import categories
from proto import load_pb2


def specialist_load_rows(session, specialists, settings, now):
    loads = logic.specialist_loads(session, [user.id for user in specialists], settings, now)
    rows = []
    for user in specialists:
        load, count = loads[user.id]
        rows.append(load_pb2.SpecialistLoad(
            specialist_id=user.id,
            full_name=user.full_name,
            load=load,
            load_index=logic.load_index(load, settings),
            active_requests=count,
        ))
    return rows


def rank_specialists(session, settings, now, category_id):
    specialists = categories.list_specialists_by_category(session, category_id)
    rows = specialist_load_rows(session, specialists, settings, now)
    rows.sort(key=lambda row: row.load_index)
    return load_pb2.DepartmentLoadResponse(specialists=rows)
