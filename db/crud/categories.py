from sqlalchemy import select

from db.models import EquipmentCategory, User


def create_category(session, name):
    category = EquipmentCategory(name=name)
    session.add(category)
    session.commit()
    return category


def get_category(session, category_id):
    return session.get(EquipmentCategory, category_id)


def list_categories(session):
    return session.scalars(select(EquipmentCategory).order_by(EquipmentCategory.name)).all()


def update_category(session, category_id, name):
    category = get_category(session, category_id)
    if category is None:
        return None
    category.name = name
    session.commit()
    return category


def delete_category(session, category_id):
    category = get_category(session, category_id)
    if category is None:
        return False
    session.delete(category)
    session.commit()
    return True


def add_competence(session, specialist_id, category_id):
    user = session.get(User, specialist_id)
    category = get_category(session, category_id)
    if user is None or category is None:
        raise ValueError("Нет такого специалиста или категории")
    if user.role != "specialist":
        raise ValueError(f"{user.full_name} не технический специалист")
    if category not in user.categories:
        user.categories.append(category)
        session.commit()
    return user


def remove_competence(session, specialist_id, category_id):
    user = session.get(User, specialist_id)
    category = get_category(session, category_id)
    if user and category in user.categories:
        user.categories.remove(category)
        session.commit()
    return user


def list_specialists_by_category(session, category_id):
    query = (
        select(User)
        .join(User.categories)
        .where(EquipmentCategory.id == category_id, User.role == "specialist", User.is_active)
        .order_by(User.full_name)
    )
    return session.scalars(query).all()
