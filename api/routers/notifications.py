from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_current_user, get_db
from api.schemas.notifications import NotificationOut
from db.crud import notifications

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def list_notifications(unread: bool = False, session=Depends(get_db), user=Depends(get_current_user)):
    return notifications.list_notifications(session, user.id, unread_only=unread)


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: int, session=Depends(get_db), user=Depends(get_current_user)):
    notification = notifications.get_notification(session, notification_id)
    if notification is None or notification.user_id != user.id:
        raise HTTPException(404, "Уведомление не найдено")
    return notifications.mark_read(session, notification_id)
