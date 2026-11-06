from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer

from api.security import decode_token
from db.crud import settings, users
from db.database import SessionLocal

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_settings(session=Depends(get_db)):
    return settings.get_all_settings(session)


def get_load_client(request: Request):
    """Клиент сервиса загрузки, созданный в lifespan приложения."""
    return request.app.state.load_client


def get_trace_id(request: Request):
    """Идентификатор HTTP-запроса для сквозных логов, его же получает сервис загрузки."""
    return request.state.trace_id


def get_current_user(token: str = Depends(oauth2_scheme), session=Depends(get_db)):
    user_id = decode_token(token)
    user = users.get_user(session, user_id) if user_id else None
    if user is None or not user.is_active:
        raise HTTPException(401, "Неверный или просроченный токен", headers={"WWW-Authenticate": "Bearer"})
    return user


def require_role(*roles):
    def checker(user=Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(403, "Недостаточно прав")
        return user
    return checker
