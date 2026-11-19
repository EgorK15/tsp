TEMPLATES = {
    "request_created": "Новая заявка №{request_id} «{title}» по сделке №{deal_id}",
    "request_assigned": "Вам назначена заявка №{request_id} «{title}», {role}",
    "request_ready": "КП по заявке №{request_id} «{title}» готово",
    "request_overdue": "Заявка №{request_id} «{title}» просрочена: {age} раб. дн. с создания",
}


def render_text(event_type, payload):
    fields = dict(payload)
    if event_type == "request_assigned":
        fields["role"] = "вы основной исполнитель" if fields.get("is_main") else "вы соисполнитель"
    try:
        return TEMPLATES[event_type].format(**fields)
    except KeyError:
        return f"Заявка №{fields.get('request_id', '?')}: {event_type}"


def render(event):
    """Уведомление для пользователя: текст по шаблону типа события и данные события для клиента."""
    return {
        "id": event.notification_id,
        "event_type": event.event_type,
        "text": render_text(event.event_type, event.payload),
        "payload": event.payload,
        "created_at": event.created_at.isoformat(),
    }
