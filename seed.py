from sqlalchemy import text

from db.crud import categories, deals, stages, users
from db.database import Base, SessionLocal
from db.models import AxisStatus

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
    pass


def main():
    with SessionLocal() as session:
        clear(session)
        seed_base(session)
        seed_requests(session)
        print("Тестовые данные загружены")
        print("Пользователей:", len(users.list_users(session)))
        print("Сделок:", len(deals.list_deals(session)))


if __name__ == "__main__":
    main()
