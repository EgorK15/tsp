from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from db.crud import categories, deals, requests, stages, users
from db.database import Base, SessionLocal
from db.models import AxisStatus, Request, RequestAssignee, StageHistory

S = AxisStatus

STAGES = [
    ("new", "Новая", "queue"),
    ("in_work", "В работе", "queue"),
    ("clarification", "Уточнение у клиента", "queue"),
    ("ready", "КП готово", "ready"),
    ("presented", "Презентация проведена", "presented"),
    ("lost", "Проигрыш", "lost"),
]

CATEGORIES = ["Насосы", "Компрессоры", "Теплообменники", "АСУ ТП", "Котельное оборудование"]

# (сделка, категория, название, путь по стадиям [(код, сколько дней назад)], основной, соисполнители)
REQUESTS = [
    (1, 1, "Подбор насосов первого подъёма", [("new", 12), ("in_work", 11)], 5, []),
    (1, 4, "Шкаф управления насосной станцией", [("new", 15), ("in_work", 14), ("ready", 10)], 7, []),
    (2, 2, "Винтовые компрессоры, 2 шт.", [("new", 5), ("in_work", 4), ("clarification", 2)], 5, [6]),
    (2, 3, "Концевой охладитель сжатого воздуха", [("new", 1)], None, []),
    (3, 4, "ПЛК и SCADA для котельной", [("new", 25), ("in_work", 22)], 7, []),
    (4, 3, "Пластинчатые теплообменники ГВС",
     [("new", 30), ("in_work", 29), ("ready", 24), ("presented", 20)], 8, []),
    (4, 3, "Теплообменники отопления", [("new", 3), ("in_work", 2)], 6, [8]),
    (5, 5, "Водогрейный котёл 2 МВт с горелкой", [("new", 18), ("in_work", 17)], 8, []),
    (5, 1, "Сетевые насосы котельной", [("new", 9), ("in_work", 8), ("ready", 2)], 5, []),
    (6, 1, "Дожимная насосная станция", [("new", 20), ("in_work", 19), ("ready", 12)], 5, [6]),
    (6, 4, "Автоматика ДНС", [("new", 40), ("in_work", 38), ("ready", 33), ("presented", 28)], 7, []),
    (7, 2, "Поршневые компрессоры", [("new", 35), ("in_work", 33), ("lost", 20)], 6, []),
    (8, 4, "Телемеханика насосных станций", [("new", 0)], None, []),
    (8, 1, "Замена насосов на КНС-3", [("new", 4), ("in_work", 3)], 5, []),
]


def clear(session):
    tables = [t.name for t in Base.metadata.sorted_tables]
    session.execute(text(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE"))
    session.commit()


def seed_base(session):
    for i, (code, name, kind) in enumerate(STAGES, start=1):
        stages.create_stage(session, code, name, kind, i)

    cats = {name: categories.create_category(session, name) for name in CATEGORIES}

    users.create_user(session, "head@techqueue.ru", "Орлов Сергей Петрович", "head123", "head")
    m1 = users.create_user(session, "ivanova@techqueue.ru", "Иванова Анна Сергеевна", "manager123")
    m2 = users.create_user(session, "petrov@techqueue.ru", "Петров Илья Олегович", "manager123")
    m3 = users.create_user(session, "smirnova@techqueue.ru", "Смирнова Ольга Викторовна", "manager123")

    specialists = [
        ("kuznetsov@techqueue.ru", "Кузнецов Дмитрий Андреевич", ["Насосы", "Компрессоры"]),
        ("volkov@techqueue.ru", "Волков Артём Игоревич", ["Компрессоры", "Теплообменники"]),
        ("sokolova@techqueue.ru", "Соколова Мария Павловна", ["АСУ ТП"]),
        ("lebedev@techqueue.ru", "Лебедев Никита Романович", ["Теплообменники", "Котельное оборудование"]),
    ]
    for email, name, comps in specialists:
        user = users.create_user(session, email, name, "spec123", "specialist")
        for c in comps:
            categories.add_competence(session, user.id, cats[c].id)

    deals.create_deal(session, m1.id, "Насосная станция водозабора", "ООО «Водоканал-Сервис»", 4_500_000,
                      S.confirmed, S.confirmed, S.stated, 80)
    deals.create_deal(session, m1.id, "Компрессорная для цеха окраски", "АО «Самаравтопром»", 2_100_000,
                      S.stated, S.stated, S.confirmed, 60)
    deals.create_deal(session, m1.id, "Модернизация АСУ котельной", "МУП «Теплосеть»", 900_000,
                      S.none, S.stated, S.none, 30)
    deals.create_deal(session, m2.id, "Теплообменники для ИТП", "ООО «ЖилСтрой»", 1_350_000,
                      S.confirmed, S.stated, S.confirmed, 90)
    deals.create_deal(session, m2.id, "Блочная котельная 2 МВт", "ООО «АгроХолдинг Поволжье»", 12_000_000,
                      S.stated, S.none, S.stated, 40)
    deals.create_deal(session, m2.id, "Дожимные насосы", "ПАО «НефтеТранс»", 7_800_000,
                      S.confirmed, S.confirmed, S.confirmed, 100)
    deals.create_deal(session, m3.id, "Воздушные компрессоры", "ООО «Пищекомбинат»", 600_000,
                      S.none, S.none, S.stated, 10)
    deals.create_deal(session, m3.id, "Диспетчеризация насосных", "ГУП «Водоснабжение»", 3_200_000,
                      S.stated, S.confirmed, S.stated, 70)


def seed_requests(session):
    now = datetime.now(timezone.utc)
    stage_ids = {s.code: s.id for s in stages.list_stages(session)}
    for deal_id, category_id, title, path, main_id, co_ids in REQUESTS:
        deal = deals.get_deal(session, deal_id)
        created = now - timedelta(days=path[0][1], hours=2)
        request = Request(deal_id=deal_id, category_id=category_id, created_by=deal.manager_id,
                          title=title, created_at=created)
        prev = None
        for code, days in path:
            at = now - timedelta(days=days, hours=2)
            by = deal.manager_id if code in ("new", "presented", "lost") else main_id
            request.history.append(StageHistory(from_stage_id=prev, to_stage_id=stage_ids[code],
                                                changed_by=by, changed_at=at))
            prev = stage_ids[code]
            if code == "ready":
                request.ready_at = at
            if code in ("presented", "lost"):
                request.closed_at = at
        request.stage_id = prev
        request.stage_changed_at = at
        if main_id:
            request.assignees.append(RequestAssignee(specialist_id=main_id, is_main=True, assigned_at=created))
        for co_id in co_ids:
            request.assignees.append(RequestAssignee(specialist_id=co_id, is_main=False, assigned_at=created))
        session.add(request)
    session.commit()


def main():
    with SessionLocal() as session:
        clear(session)
        seed_base(session)
        seed_requests(session)
        print("Тестовые данные загружены")
        print("Пользователей:", len(users.list_users(session)))
        print("Сделок:", len(deals.list_deals(session)))
        print("Заявок:", len(requests.list_requests(session)))


if __name__ == "__main__":
    main()
