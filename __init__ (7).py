from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from typing import List

from app.db.session import get_db
from app.models.models import User, Notification, JobAlert
from app.schemas.schemas import NotificationResponse, JobAlertCreateRequest, JobAlertResponse, PaginatedResponse
from app.api.deps import get_current_user

router = APIRouter(tags=["Notifications & Alerts"])


# ── Notifications ─────────────────────────────────────────────────────────────

@router.get("/notifications", response_model=PaginatedResponse)
async def list_notifications(
    unread_only: bool = False,
    page: int = 1,
    page_size: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    filters = [Notification.user_id == current_user.id]
    if unread_only:
        filters.append(Notification.is_read == False)

    from sqlalchemy import and_
    condition = and_(*filters)

    count = await db.execute(select(func.count()).select_from(Notification).where(condition))
    total = count.scalar()

    result = await db.execute(
        select(Notification)
        .where(condition)
        .order_by(Notification.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = result.scalars().all()

    return PaginatedResponse(
        total=total, page=page, page_size=page_size,
        pages=-(-total // page_size),
        items=[NotificationResponse.model_validate(n) for n in items],
    )


@router.get("/notifications/unread-count")
async def unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(func.count()).select_from(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read == False)
    )
    return {"unread_count": result.scalar()}


@router.patch("/notifications/{notification_id}/read", response_model=NotificationResponse)
async def mark_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    return notif


@router.patch("/notifications/mark-all-read")
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read == False)
        .values(is_read=True)
    )
    return {"message": "All notifications marked as read"}


@router.delete("/notifications/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    await db.delete(notif)


# ── Job Alerts ────────────────────────────────────────────────────────────────

@router.get("/alerts", response_model=List[JobAlertResponse])
async def list_alerts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(JobAlert)
        .where(JobAlert.user_id == current_user.id)
        .order_by(JobAlert.created_at.desc())
    )
    return result.scalars().all()


@router.post("/alerts", response_model=JobAlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    payload: JobAlertCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Limit: 10 alerts per user
    count = await db.execute(
        select(func.count()).select_from(JobAlert).where(JobAlert.user_id == current_user.id)
    )
    if count.scalar() >= 10:
        raise HTTPException(status_code=400, detail="Maximum of 10 job alerts allowed")

    alert = JobAlert(user_id=current_user.id, **payload.model_dump())
    db.add(alert)
    await db.flush()
    return alert


@router.patch("/alerts/{alert_id}", response_model=JobAlertResponse)
async def update_alert(
    alert_id: str,
    payload: JobAlertCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(JobAlert).where(JobAlert.id == alert_id, JobAlert.user_id == current_user.id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(alert, field, value)
    return alert


@router.patch("/alerts/{alert_id}/toggle", response_model=JobAlertResponse)
async def toggle_alert(
    alert_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(JobAlert).where(JobAlert.id == alert_id, JobAlert.user_id == current_user.id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_active = not alert.is_active
    return alert


@router.delete("/alerts/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(JobAlert).where(JobAlert.id == alert_id, JobAlert.user_id == current_user.id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    await db.delete(alert)
