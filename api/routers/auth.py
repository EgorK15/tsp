from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from api.deps import get_current_user, get_db
from api.schemas.users import Token, UserOut, UserRegister
from api.security import create_access_token
from db.crud import users

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(data: UserRegister, session=Depends(get_db)):
    return users.create_user(session, data.email, data.full_name, data.password)


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), session=Depends(get_db)):
    user = users.get_user_by_email(session, form.username)
    if user is None or not users.check_password(user, form.password) or not user.is_active:
        raise HTTPException(401, "Неверный e-mail или пароль", headers={"WWW-Authenticate": "Bearer"})
    return Token(access_token=create_access_token(user))


@router.get("/me", response_model=UserOut)
def me(user=Depends(get_current_user)):
    return user
