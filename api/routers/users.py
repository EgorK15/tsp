from fastapi import APIRouter, Depends, HTTPException, Response

from api.deps import get_current_user, get_db, require_role
from api.schemas.users import RoleUpdate, UserOut, UserUpdate
from db.crud import users

router = APIRouter(prefix="/users", tags=["users"])


def get_user_or_404(session, user_id):
    user = users.get_user(session, user_id)
    if user is None:
        raise HTTPException(404, "Пользователь не найден")
    return user


@router.get("", response_model=list[UserOut])
def list_users(role: str | None = None, session=Depends(get_db), user=Depends(require_role("head"))):
    return users.list_users(session, role=role)


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, session=Depends(get_db), user=Depends(get_current_user)):
    if user.role != "head" and user.id != user_id:
        raise HTTPException(403, "Недостаточно прав")
    return get_user_or_404(session, user_id)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, data: UserUpdate, session=Depends(get_db), user=Depends(get_current_user)):
    if user.role != "head" and user.id != user_id:
        raise HTTPException(403, "Недостаточно прав")
    fields = data.model_dump(exclude_unset=True)
    if "is_active" in fields and user.role != "head":
        raise HTTPException(403, "Блокировать пользователей может только руководитель")
    get_user_or_404(session, user_id)
    return users.update_user(session, user_id, **fields)


@router.patch("/{user_id}/role", response_model=UserOut)
def set_role(user_id: int, data: RoleUpdate, session=Depends(get_db), user=Depends(require_role("head"))):
    get_user_or_404(session, user_id)
    return users.set_role(session, user_id, data.role, user)


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, session=Depends(get_db), user=Depends(require_role("head"))):
    get_user_or_404(session, user_id)
    users.deactivate_user(session, user_id)
    return Response(status_code=204)
