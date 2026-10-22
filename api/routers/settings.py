from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_db, require_role
from api.schemas.dashboard import SettingIn, SettingOut
from db.crud import settings

router = APIRouter(prefix="/settings", tags=["settings"])


def check_value(key, value):
    """Значение должно быть того же вида, что и по умолчанию: число или объект с теми же ключами."""
    default = settings.DEFAULTS[key]
    if isinstance(default, dict) != isinstance(value, dict):
        raise HTTPException(400, "Нужен объект" if isinstance(default, dict) else "Нужно число")
    if isinstance(default, dict) and value.keys() != default.keys():
        raise HTTPException(400, f"Нужен объект с ключами {', '.join(default)}")
    values = value.values() if isinstance(value, dict) else [value]
    if any(v <= 0 for v in values):
        raise HTTPException(400, "Значения должны быть положительными")


@router.get("")
def list_settings(session=Depends(get_db), user=Depends(require_role("head"))):
    return settings.get_all_settings(session)


@router.put("/{key}", response_model=SettingOut)
def set_setting(key: str, data: SettingIn, session=Depends(get_db), user=Depends(require_role("head"))):
    if key not in settings.DEFAULTS:
        raise HTTPException(404, "Нет такой настройки")
    check_value(key, data.value)
    return settings.set_setting(session, key, data.value, user.id)
