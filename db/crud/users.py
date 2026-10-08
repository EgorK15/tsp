import hashlib
import os

from sqlalchemy import select

from db.models import User

ROLES = ("manager", "specialist", "head")


def hash_password(password):
    salt = os.urandom(16).hex()
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return f"{salt}${h}"


def check_password(user, password):
    salt, h = user.password_hash.split("$")
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex() == h


def create_user(session, email, full_name, password, role="manager"):
    if role not in ROLES:
        raise ValueError(f"Неизвестная роль: {role}")
    if get_user_by_email(session, email):
        raise ValueError(f"Пользователь с e-mail {email} уже есть")
    user = User(email=email, full_name=full_name, password_hash=hash_password(password), role=role)
    session.add(user)
    session.commit()
    return user


def get_user(session, user_id):
    return session.get(User, user_id)


def get_user_by_email(session, email):
    return session.scalar(select(User).where(User.email == email))


def list_users(session, role=None):
    query = select(User).order_by(User.id)
    if role:
        query = query.where(User.role == role)
    return session.scalars(query).all()


def update_user(session, user_id, **fields):
    user = get_user(session, user_id)
    if user is None:
        return None
    if "password" in fields:
        user.password_hash = hash_password(fields.pop("password"))
    for key, value in fields.items():
        setattr(user, key, value)
    session.commit()
    return user


def set_role(session, user_id, role, by_user):
    """Выдать роль может только руководитель."""
    if by_user.role != "head":
        raise ValueError("Менять роли может только руководитель")
    if role not in ROLES:
        raise ValueError(f"Неизвестная роль: {role}")
    return update_user(session, user_id, role=role)


def deactivate_user(session, user_id):
    return update_user(session, user_id, is_active=False)


def delete_user(session, user_id):
    user = get_user(session, user_id)
    if user is None:
        return False
    session.delete(user)
    session.commit()
    return True
