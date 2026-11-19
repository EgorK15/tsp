TEMPLATES = {
    "request_created": "Новая заявка №{request_id} «{title}» по сделке №{deal_id}",
    "request_assigned": "Вам назначена заявка №{request_id} «{title}», {role}",
    "request_ready": "КП по заявке №{request_id} «{title}» готово",
    "request_overdue": "Заявка №{request_id} «{title}» просрочена: {age} раб. дн. с создания",
}


def render(event):
    """Уведомление для пользователя: текст по шаблону типа события и данные события для клиента."""
    fields = dict(event.payload)
    if event.event_type == "request_assigned":
        fields["role"] = "вы основной исполнитель" if fields.get("is_main") else "вы соисполнитель"
    try:
        text = TEMPLATES[event.event_type].format(**fields)
    except KeyError:
        text = f"Заявка №{fields.get('request_id', '?')}: {event.event_type}"
    return {
        "id": event.notification_id,
        "event_type": event.event_type,
        "text": text,
        "payload": event.payload,
        "created_at": event.created_at.isoformat(),
    }
