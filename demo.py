from datetime import date, datetime, timezone

from sqlalchemy.exc import IntegrityError

from db import dashboard, logic
from db.crud import assignees, categories, deals, notifications, requests, settings, users
from db.database import SessionLocal
from db.models import AxisStatus, RequestAssignee

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


def show_request(r, now):
    p = logic.deal_priority(r.deal)
    print(f"  #{r.id} {r.title} [{r.stage.name}] приоритет {p}, возраст {logic.request_age(r, now)} раб. дн.")


def show_load(rows):
    for user, load, index in rows:
        print(f"  {user.full_name}: загрузка {load:.2f}, индекс {index:.0f}%")


def demo_create_request(session):
    title("Сценарий 2: заявка на КП по сделке")
    cfg = settings.get_all_settings(session)
    manager = users.get_user_by_email(session, "ivanova@techqueue.ru")
    head = users.list_users(session, role="head")[0]

    for deal in deals.list_deals(session, manager_id=manager.id):
        verdict = "вернуть менеджеру" if logic.needs_return(deal, cfg) else "можно в работу"
        print(f"Сделка #{deal.id} {deal.title}: приоритет {logic.deal_priority(deal)}, "
              f"ТЗ {deal.tz_percent}% -> {verdict}")

    deal = deals.get_deal(session, 2)
    compressors = [c for c in categories.list_categories(session) if c.name == "Компрессоры"][0]
    request = requests.create_request(session, deal.id, compressors.id, "Компрессор для резервной линии",
                                      "Нужен второй компрессор той же серии", manager.id)
    print(f"Создана заявка #{request.id} «{request.title}», стадия: {request.stage.name}")
    print("Приоритет:", logic.deal_priority(request.deal),
          "| вернуть менеджеру:", logic.needs_return(request.deal, cfg))

    requests.update_request(session, request.id, description="Второй компрессор той же серии, 7,5 бар")
    print("Описание исправлено:", request.description)
    try:
        requests.update_request(session, request.id, stage_id=4)
    except ValueError as e:
        print("Смена стадии через update_request:", e)

    last = notifications.list_notifications(session, head.id, unread_only=True)[-1]
    print("Уведомление руководителю:", last.event_type, last.payload)
    return request


def demo_assign(session, request):
    title("Сценарий 3: назначение исполнителей")
    cfg = settings.get_all_settings(session)
    now = datetime.now(timezone.utc)
    head = users.list_users(session, role="head")[0]
    manager = users.get_user_by_email(session, "ivanova@techqueue.ru")

    print(f"Подсказка специалистов по категории «{request.category.name}»:")
    suggested = logic.suggest_specialists(session, request.category_id, cfg, now)
    show_load(suggested)
    main, co = suggested[0][0], suggested[1][0]

    try:
        assignees.assign(session, request.id, main.id, by_user=manager)
    except ValueError as e:
        print("Менеджер назначает исполнителя:", e)
    try:
        assignees.assign(session, request.id, manager.id, by_user=head)
    except ValueError as e:
        print("Менеджер в роли исполнителя:", e)

    assignees.assign(session, request.id, main.id, [co.id], by_user=head)
    print("Назначены:")
    for a in assignees.list_assignees(session, request.id):
        print("  -", a.specialist.full_name, "(основной)" if a.is_main else "(соисполнитель)")

    try:
        co_row = session.get(RequestAssignee, (request.id, co.id))
        co_row.is_main = True
        session.commit()
    except IntegrityError:
        session.rollback()
        print("Второй основной исполнитель напрямую в БД: IntegrityError (индекс uq_request_main)")

    for user in (main, co):
        last = notifications.list_notifications(session, user.id, unread_only=True)[-1]
        print(f"Уведомление {user.full_name}:", last.event_type, last.payload)
    return main


def demo_prepare_kp(session, request, specialist):
    title("Сценарий 4: подготовка КП")
    cfg = settings.get_all_settings(session)
    now = datetime.now(timezone.utc)
    manager = request.deal.manager
    head = users.list_users(session, role="head")[0]

    print(f"Мои заявки ({specialist.full_name}):")
    for r in requests.my_requests(session, specialist.id, cfg, now):
        show_request(r, now)

    try:
        requests.change_stage(session, request.id, "ready", specialist)
    except ValueError as e:
        print("Сразу в «КП готово»:", e)

    for code in ("in_work", "clarification", "in_work"):
        requests.change_stage(session, request.id, code, specialist)
        print("Стадия:", request.stage.name)

    requests.update_request(session, request.id, result_url="https://disk.techqueue.ru/kp/compressor.pdf")
    requests.change_stage(session, request.id, "ready", specialist)
    print("Стадия:", request.stage.name, "| ссылка на КП:", request.result_url)

    last = notifications.list_notifications(session, manager.id, unread_only=True)[-1]
    print(f"Уведомление менеджеру {manager.full_name}:", last.event_type, last.payload)

    try:
        requests.change_stage(session, request.id, "presented", specialist)
    except ValueError as e:
        print("Специалист отмечает презентацию:", e)
    requests.change_stage(session, request.id, "presented", manager)
    print("Менеджер провёл презентацию, стадия:", request.stage.name)

    try:
        requests.change_stage(session, request.id, "in_work", head)
    except ValueError as e:
        print("Вернуть закрытую заявку в работу:", e)

    print("История стадий:")
    for h in requests.request_history(session, request.id):
        from_name = h.from_stage.name if h.from_stage else "—"
        print(f"  {h.changed_at.astimezone():%d.%m %H:%M:%S} {from_name} -> {h.to_stage.name}")


def demo_dashboard(session):
    title("Сценарий 5: дашборд руководителя")
    cfg = settings.get_all_settings(session)
    now = datetime.now(timezone.utc)
    head = users.list_users(session, role="head")[0]

    print("Норматив по приоритетам (раб. дн.):", cfg["norm_days"])
    overdue = dashboard.overdue_requests(session, cfg, now)
    print("Просроченные заявки:", len(overdue))
    for r in overdue:
        show_request(r, now)

    print("Медиана рабочих дней до готового КП:")
    for p, value in dashboard.median_days_by_priority(session, cfg).items():
        print(f"  приоритет {p}: {value if value is not None else 'нет данных'}")

    print(f"Готовые КП без презентации дольше {cfg['ready_wait_days']} дней:")
    for r in dashboard.ready_without_presentation(session, cfg, now):
        print(f"  #{r.id} {r.title}, готово {r.ready_at.astimezone():%d.%m}, менеджер {r.deal.manager.full_name}")

    print("Загрузка отдела:")
    rows = dashboard.department_load(session, cfg, now)
    show_load(rows)

    busiest, _, busiest_index = max(rows, key=lambda x: x[2])
    if busiest_index > 100:
        for r in logic.active_requests(session, busiest.id):
            if not any(a.is_main and a.specialist_id == busiest.id for a in r.assignees):
                continue
            others = [x[0] for x in logic.suggest_specialists(session, r.category_id, cfg, now)
                      if x[0].id != busiest.id]
            if others:
                assignees.reassign_main(session, r.id, others[0].id)
                print(f"{busiest.full_name} перегружен, заявка #{r.id} передана: {others[0].full_name}")
                show_load(dashboard.department_load(session, cfg, now))
                break

    old_norm = cfg["norm_days"]
    settings.set_setting(session, "norm_days", {"1": 2, "2": 5, "3": 10}, head.id)
    cfg = settings.get_all_settings(session)
    print("Руководитель ужесточил норматив:", cfg["norm_days"])
    print("Просроченные заявки:", len(dashboard.overdue_requests(session, cfg, now)))
    settings.set_setting(session, "norm_days", old_norm, head.id)
    print("Норматив возвращён:", settings.get_setting(session, "norm_days"))


def demo_scheduler(session):
    title("Планировщик: снимок загрузки и контроль просрочек")
    cfg = settings.get_all_settings(session)
    now = datetime.now(timezone.utc)

    print("Снимок загрузки на", date.today())
    for s in dashboard.take_load_snapshot(session, cfg, date.today()):
        print(f"  {s.specialist.full_name}: {s.load}, активных заявок {s.active_requests}")

    created = dashboard.check_overdue(session, cfg, now)
    print("Создано уведомлений о просрочке:", len(created))
    for n in created:
        print(f"  {n.user.full_name}: заявка #{n.payload['request_id']} «{n.payload['title']}», "
              f"{n.payload['age']} раб. дн.")

    user = created[0].user if created else users.list_users(session, role="specialist")[0]
    unread = notifications.list_notifications(session, user.id, unread_only=True)
    print(f"Непрочитанных уведомлений у {user.full_name}:", len(unread))
    for n in unread:
        notifications.mark_read(session, n.id)
    print("После прочтения:", len(notifications.list_notifications(session, user.id, unread_only=True)))


def main():
    with SessionLocal() as session:
        specialist = demo_users(session)
        demo_categories(session, specialist)
        demo_deals(session)
        request = demo_create_request(session)
        main_specialist = demo_assign(session, request)
        demo_prepare_kp(session, request, main_specialist)
        demo_dashboard(session)
        demo_scheduler(session)
        requests.delete_request(session, request.id)
        users.delete_user(session, specialist.id)


if __name__ == "__main__":
    main()
