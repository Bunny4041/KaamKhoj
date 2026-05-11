"""
Notification Service
Handles in-app notifications and (optionally) email notifications.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Optional
import logging

from app.models.models import Notification, NotificationType, User
from app.core.config import settings

logger = logging.getLogger(__name__)


async def create_notification(
    db: AsyncSession,
    user_id: str,
    type: NotificationType,
    title: str,
    message: str,
    action_url: Optional[str] = None,
    meta: Optional[dict] = None,
) -> Notification:
    notif = Notification(
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        action_url=action_url,
        meta=meta or {},
    )
    db.add(notif)
    await db.flush()
    return notif


async def notify_application_received(db: AsyncSession, employer_id: str, applicant_name: str, job_title: str, application_id: str):
    await create_notification(
        db=db,
        user_id=employer_id,
        type=NotificationType.APPLICATION_RECEIVED,
        title="New Application Received",
        message=f"{applicant_name} applied for {job_title}",
        action_url=f"/applications/{application_id}",
        meta={"application_id": application_id},
    )


async def notify_application_status_changed(db: AsyncSession, applicant_id: str, status: str, job_title: str, application_id: str):
    status_messages = {
        "reviewing":   ("Application Under Review", f"Your application for {job_title} is being reviewed."),
        "shortlisted": ("🎉 You've been Shortlisted!", f"Great news! You're shortlisted for {job_title}."),
        "interview":   ("Interview Scheduled", f"An interview has been scheduled for {job_title}."),
        "offered":     ("🎊 Job Offer!", f"You have received a job offer for {job_title}!"),
        "rejected":    ("Application Update", f"Your application for {job_title} was not selected this time."),
    }
    title, message = status_messages.get(status, ("Application Update", f"Your {job_title} application status changed to {status}."))
    await create_notification(
        db=db,
        user_id=applicant_id,
        type=NotificationType.APPLICATION_STATUS,
        title=title,
        message=message,
        action_url=f"/applications/{application_id}",
        meta={"application_id": application_id, "status": status},
    )


async def notify_job_alert(db: AsyncSession, user_id: str, job_count: int, alert_name: str):
    await create_notification(
        db=db,
        user_id=user_id,
        type=NotificationType.JOB_ALERT,
        title=f"New Jobs for '{alert_name}'",
        message=f"{job_count} new job{'s' if job_count > 1 else ''} match your alert criteria.",
        action_url="/jobs/search",
        meta={"count": job_count},
    )


async def send_welcome_email(user_email: str, user_name: str):
    """Stub — integrate with aiosmtplib or SendGrid in production."""
    if not settings.EMAILS_ENABLED:
        logger.info(f"[Email stub] Welcome email to {user_email}")
        return
    # TODO: render HTML template and send via aiosmtplib


async def send_verification_email(user_email: str, user_name: str, token: str):
    verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    if not settings.EMAILS_ENABLED:
        logger.info(f"[Email stub] Verify URL for {user_email}: {verify_url}")
        return


async def send_password_reset_email(user_email: str, user_name: str, token: str):
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    if not settings.EMAILS_ENABLED:
        logger.info(f"[Email stub] Reset URL for {user_email}: {reset_url}")
        return
