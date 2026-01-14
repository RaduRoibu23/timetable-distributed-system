from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Notification, UserProfile, SchoolClass


def send_to_user(
    db: Session,
    username: str,
    message: str,
) -> Notification:
    """Send a notification to a specific user by username."""
    notification = Notification(
        username=username,
        message=message,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def send_to_class(
    db: Session,
    class_id: int,
    message: str,
) -> list[Notification]:
    """
    Send a notification to all students in a class.
    Finds all UserProfile entries with this class_id and creates notifications for each.
    """
    profiles = (
        db.query(UserProfile)
        .filter(UserProfile.class_id == class_id)
        .all()
    )

    notifications = []
    for profile in profiles:
        notif = Notification(
            username=profile.username,
            message=message,
        )
        db.add(notif)
        notifications.append(notif)

    db.commit()
    for notif in notifications:
        db.refresh(notif)
    return notifications


def get_user_notifications(
    db: Session,
    username: str,
    unread_only: bool = False,
) -> list[Notification]:
    """Get all notifications for a user, optionally filtered to unread only."""
    query = db.query(Notification).filter(Notification.username == username)
    if unread_only:
        query = query.filter(Notification.read == False)
    return query.order_by(Notification.created_at.desc()).all()


def mark_as_read(
    db: Session,
    notification_id: int,
    username: str,
) -> Notification:
    """
    Mark a notification as read. Only the owner (username) can mark it as read.
    """
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id)
        .filter(Notification.username == username)
        .first()
    )
    if not notification:
        raise ValueError(f"Notification {notification_id} not found for user {username}")

    notification.read = True
    db.commit()
    db.refresh(notification)
    return notification
