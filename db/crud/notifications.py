from datetime import datetime, timezone

from sqlalchemy import select

from db.models import Notification


def create_notification(session, user_id, event_type, payload, commit=True):
    notification = Notification(user_id=user_id, event_type=event_type, payload=payload)
    session.add(notification)
    if commit:
        session.commit()
    return notification


def list_notifications(session, user_id, unread_only=False):
    query = select(Notification).where(Notification.user_id == user_id).order_by(Notification.id)
    if unread_only:
        query = query.where(Notification.read_at.is_(None))
    return session.scalars(query).all()


def mark_read(session, notification_id):
    notification = session.get(Notification, notification_id)
    if notification is None:
        return None
    notification.read_at = datetime.now(timezone.utc)
    session.commit()
    return notification
