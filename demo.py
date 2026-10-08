from db.crud import categories, deals, users
from db.database import SessionLocal
from db.models import AxisStatus

DEMO_EMAIL = "novikov@techqueue.ru"


def title(text):
    print()
    print("=" * 60)
    print(text)
    print("=" * 60)


def demo_users(session):
    title("Пользователи: регистрация, вход, роли")

    old = users.get_user_by_email(session, DEMO_EMAIL)
    if old:
        users.delete_user(session, old.id)

    user = users.create_user(session, DEMO_EMAIL, "Новиков Павел Андреевич", "qwerty")
    print("Зарегистрирован:", user.full_name, "| роль:", user.role)

    try:
        users.create_user(session, DEMO_EMAIL, "Другой Новиков", "123")
    except ValueError as e:
        print("Повторная регистрация:", e)

    print("Вход с верным паролем:", users.check_password(user, "qwerty"))
    print("Вход с неверным паролем:", users.check_password(user, "12345"))

    manager = users.get_user_by_email(session, "ivanova@techqueue.ru")
    try:
        users.set_role(session, user.id, "specialist", manager)
    except ValueError as e:
        print("Менеджер выдаёт роль:", e)

    head = users.list_users(session, role="head")[0]
    users.set_role(session, user.id, "specialist", head)
    print("Руководитель выдал роль specialist, теперь роль:", user.role)

    for role in users.ROLES:
        names = [u.full_name for u in users.list_users(session, role=role)]
        print(f"{role}: {', '.join(names)}")
    return user


def demo_categories(session, specialist):
    title("Справочник категорий и компетенции специалистов")

    category = categories.create_category(session, "Вентиляционное оборудование")
    print("Добавлена категория:", category.name)
    categories.update_category(session, category.id, "Вентиляция и кондиционирование")
    print("Переименована в:", category.name)

    categories.add_competence(session, specialist.id, category.id)
    pumps = [c for c in categories.list_categories(session) if c.name == "Насосы"][0]
    categories.add_competence(session, specialist.id, pumps.id)
    print(specialist.full_name, "компетенции:", [c.name for c in specialist.categories])

    print("Специалисты по категории «Насосы»:")
    for s in categories.list_specialists_by_category(session, pumps.id):
        print("  -", s.full_name)

    categories.remove_competence(session, specialist.id, pumps.id)
    print("После снятия компетенции:", [c.name for c in specialist.categories])

    manager = users.get_user_by_email(session, "ivanova@techqueue.ru")
    try:
        categories.add_competence(session, manager.id, pumps.id)
    except ValueError as e:
        print("Компетенция менеджеру:", e)

    categories.delete_category(session, category.id)
    print("Категория удалена, компетенции специалиста:", [c.name for c in specialist.categories])
    print("Все категории:", [c.name for c in categories.list_categories(session)])


def demo_deals(session):
    title("Сделки менеджера")

    manager = users.get_user_by_email(session, "ivanova@techqueue.ru")
    other = users.get_user_by_email(session, "petrov@techqueue.ru")
    head = users.list_users(session, role="head")[0]

    deal = deals.create_deal(session, manager.id, "Насосы для градирни", "ООО «ХимПром»", 1_500_000,
                             budget_status=AxisStatus.stated)
    print(f"Создана сделка #{deal.id}: {deal.title}, клиент {deal.client_name}, сумма {deal.amount}")

    deal = deals.get_deal(session, deal.id)
    print("Оси:", deal.budget_status.value, deal.timeline_status.value, deal.need_status.value,
          "| ТЗ готово на", deal.tz_percent, "%")

    deals.update_deal(session, deal.id, manager.id, timeline_status=AxisStatus.confirmed,
                      need_status=AxisStatus.confirmed, tz_percent=75)
    print("После правки:", deal.budget_status.value, deal.timeline_status.value, deal.need_status.value,
          "| ТЗ готово на", deal.tz_percent, "%")

    try:
        deals.update_deal(session, deal.id, other.id, amount=1)
    except ValueError as e:
        print("Чужой менеджер правит сделку:", e)

    try:
        deals.update_deal(session, deal.id, manager.id, tz_percent=150)
    except Exception as e:
        session.rollback()
        print("tz_percent = 150:", type(e).__name__, "(сработал CHECK в БД)")

    print(f"Сделки менеджера {manager.full_name}:")
    for d in deals.list_deals(session, manager_id=manager.id):
        print(f"  #{d.id} {d.title} — {d.amount}")

    deals.delete_deal(session, deal.id, head.id)
    print("Руководитель удалил сделку, есть ли она:", deals.get_deal(session, deal.id) is not None)

    print("Все сделки (вид руководителя):")
    for d in deals.list_deals(session):
        print(f"  #{d.id} {d.title} [{d.manager.full_name}]")


def main():
    with SessionLocal() as session:
        specialist = demo_users(session)
        demo_categories(session, specialist)
        demo_deals(session)
        users.delete_user(session, specialist.id)


if __name__ == "__main__":
    main()
