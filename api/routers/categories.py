from fastapi import APIRouter, Depends, HTTPException, Response

from api.deps import get_current_user, get_db, require_role
from api.schemas.categories import CategoryIn, CategoryOut, StageOut
from api.schemas.users import UserOut
from db.crud import categories, stages, users

router = APIRouter(tags=["categories"])


def get_category_or_404(session, category_id):
    category = categories.get_category(session, category_id)
    if category is None:
        raise HTTPException(404, "Категория не найдена")
    return category


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(session=Depends(get_db), user=Depends(get_current_user)):
    return categories.list_categories(session)


@router.post("/categories", response_model=CategoryOut, status_code=201)
def create_category(data: CategoryIn, session=Depends(get_db), user=Depends(require_role("head"))):
    return categories.create_category(session, data.name)


@router.patch("/categories/{category_id}", response_model=CategoryOut)
def update_category(category_id: int, data: CategoryIn, session=Depends(get_db),
                    user=Depends(require_role("head"))):
    get_category_or_404(session, category_id)
    return categories.update_category(session, category_id, data.name)


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(category_id: int, session=Depends(get_db), user=Depends(require_role("head"))):
    get_category_or_404(session, category_id)
    categories.delete_category(session, category_id)
    return Response(status_code=204)


@router.get("/categories/{category_id}/specialists", response_model=list[UserOut])
def category_specialists(category_id: int, session=Depends(get_db), user=Depends(require_role("head"))):
    get_category_or_404(session, category_id)
    return categories.list_specialists_by_category(session, category_id)


@router.get("/users/{user_id}/competences", response_model=list[CategoryOut])
def list_competences(user_id: int, session=Depends(get_db), user=Depends(get_current_user)):
    if user.role != "head" and user.id != user_id:
        raise HTTPException(403, "Недостаточно прав")
    specialist = users.get_user(session, user_id)
    if specialist is None:
        raise HTTPException(404, "Пользователь не найден")
    return specialist.categories


@router.post("/users/{user_id}/competences/{category_id}", response_model=list[CategoryOut])
def add_competence(user_id: int, category_id: int, session=Depends(get_db), user=Depends(require_role("head"))):
    get_category_or_404(session, category_id)
    return categories.add_competence(session, user_id, category_id).categories


@router.delete("/users/{user_id}/competences/{category_id}", status_code=204)
def remove_competence(user_id: int, category_id: int, session=Depends(get_db),
                      user=Depends(require_role("head"))):
    categories.remove_competence(session, user_id, category_id)
    return Response(status_code=204)


@router.get("/stages", response_model=list[StageOut])
def list_stages(session=Depends(get_db), user=Depends(get_current_user)):
    return stages.list_stages(session)
