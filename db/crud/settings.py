from sqlalchemy import select

from db.models import Setting

DEFAULTS = {
    "norm_days": {"1": 5, "2": 10, "3": 15},
    "priority_weight": {"1": 3, "2": 2, "3": 1},
    "load_norm": 10,
    "ready_wait_days": 7,
    "tz_min_percent": 50,
}


def get_setting(session, key, default=None):
    setting = session.get(Setting, key)
    if setting is not None:
        return setting.value
    return DEFAULTS.get(key, default)


def set_setting(session, key, value, user_id):
    setting = session.get(Setting, key)
    if setting is None:
        setting = Setting(key=key)
        session.add(setting)
    setting.value = value
    setting.updated_by = user_id
    session.commit()
    return setting


def get_all_settings(session):
    """Настройки из БД поверх значений по умолчанию."""
    result = dict(DEFAULTS)
    for setting in session.scalars(select(Setting)):
        result[setting.key] = setting.value
    return result
