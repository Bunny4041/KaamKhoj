from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List

from app.db.session import get_db
from app.models.models import User, Job, Application, JobStatus, ApplicationStatus, UserRole
from app.schemas.schemas import (
    ApplicationCreateRequest, ApplicationStatusUpdateRequest, ApplicationResponse, PaginatedResponse
)
from app.api.deps import get_current_user, get_current_employer
from app.services.notification_service import (
    notify_application_received, notify_application_status_changed
)

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.post("/{job_id}", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def apply_for_job(
    job_id: str,
    payload: ApplicationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != UserRole.JOBSEEKER:
        raise HTTPException(status_code=403, detail="Only job seekers can apply")

    # Check job exists and is active
    result = await db.execute(
        select(Job).options(selectinload(Job.company)).where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="This job is no longer accepting applications")

    # Prevent duplicate applications
    existing = await db.execute(
        select(Application).where(
            Application.job_id == job_id,
            Application.applicant_id == current_user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="You have already applied for this job")

    application = Application(
        job_id=job_id,
        applicant_id=current_user.id,
        cover_letter=payload.cover_letter,
        resume_url=current_user.resume_url,  # snapshot
        expected_ctc_lpa=payload.expected_ctc_lpa or current_user.expected_ctc_lpa,
        notice_period_days=payload.notice_period_days or current_user.notice_period_days,
    )
    db.add(application)

    # Increment job application count
    job.applications_count += 1

    await db.flush()

    # Notify employer
    employer_id = job.company.owner_id
    await notify_application_received(
        db, employer_id, current_user.full_name, job.title, application.id
    )

    # Reload with relations
    await db.refresh(application)
    result = await db.execute(
        select(Application)
        .options(selectinload(Application.job).selectinload(Job.company), selectinload(Application.applicant))
        .where(Application.id == application.id)
    )
    return result.scalar_one()


@router.get("/me", response_model=PaginatedResponse)
async def my_applications(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    base = select(Application).where(Application.applicant_id == current_user.id)

    count = await db.execute(select(func.count()).select_from(Application).where(Application.applicant_id == current_user.id))
    total = count.scalar()

    result = await db.execute(
        base
        .options(selectinload(Application.job).selectinload(Job.company), selectinload(Application.applicant))
        .order_by(Application.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = result.scalars().all()

    return PaginatedResponse(
        total=total, page=page, page_size=page_size,
        pages=-(-total // page_size),
        items=[ApplicationResponse.model_validate(a) for a in items],
    )


@router.get("/{application_id}", response_model=ApplicationResponse)
async def get_application(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Application)
        .options(selectinload(Application.job).selectinload(Job.company), selectinload(Application.applicant))
        .where(Application.id == application_id)
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Only applicant or employer can view
    is_applicant = app.applicant_id == current_user.id
    is_employer = current_user.company and app.job.company_id == current_user.company.id
    if not (is_applicant or is_employer or current_user.role == UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Access denied")

    return app


@router.patch("/{application_id}/status", response_model=ApplicationResponse)
async def update_application_status(
    application_id: str,
    payload: ApplicationStatusUpdateRequest,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Application)
        .options(selectinload(Application.job).selectinload(Job.company), selectinload(Application.applicant))
        .where(Application.id == application_id)
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if not current_user.company or app.job.company_id != current_user.company.id:
        raise HTTPException(status_code=403, detail="Not authorised to update this application")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(app, field, value)

    # Notify applicant of status change
    await notify_application_status_changed(
        db, app.applicant_id, payload.status.value, app.job.title, app.id
    )

    return app


@router.patch("/{application_id}/withdraw", response_model=ApplicationResponse)
async def withdraw_application(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Application)
        .options(selectinload(Application.job).selectinload(Job.company), selectinload(Application.applicant))
        .where(Application.id == application_id)
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.applicant_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your application")
    if app.status in (ApplicationStatus.OFFERED, ApplicationStatus.REJECTED):
        raise HTTPException(status_code=400, detail=f"Cannot withdraw a {app.status} application")

    app.status = ApplicationStatus.WITHDRAWN
    return app


@router.get("/job/{job_id}", response_model=PaginatedResponse)
async def applications_for_job(
    job_id: str,
    status: ApplicationStatus = None,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not current_user.company or job.company_id != current_user.company.id:
        raise HTTPException(status_code=403, detail="Not your job")

    filters = [Application.job_id == job_id]
    if status:
        filters.append(Application.status == status)

    from sqlalchemy import and_
    count = await db.execute(select(func.count()).select_from(Application).where(and_(*filters)))
    total = count.scalar()

    result = await db.execute(
        select(Application)
        .options(selectinload(Application.job).selectinload(Job.company), selectinload(Application.applicant))
        .where(and_(*filters))
        .order_by(Application.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = result.scalars().all()

    return PaginatedResponse(
        total=total, page=page, page_size=page_size,
        pages=-(-total // page_size),
        items=[ApplicationResponse.model_validate(a) for a in items],
    )
