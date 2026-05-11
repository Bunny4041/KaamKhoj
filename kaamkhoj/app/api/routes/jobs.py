from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, update
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import datetime, timezone
import re, uuid

from app.db.session import get_db
from app.models.models import User, Job, Company, JobStatus, JobType, WorkMode, ExperienceLevel
from app.schemas.schemas import (
    JobCreateRequest, JobUpdateRequest, JobResponse, JobListResponse, PaginatedResponse
)
from app.api.deps import get_current_user, get_current_employer
from app.core.config import settings

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def slugify_job(title: str, job_id: str) -> str:
    s = title.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s]+", "-", s)
    return f"{s}-{job_id[:8]}"


def build_job_query(
    q: Optional[str] = None,
    city: Optional[str] = None,
    category: Optional[str] = None,
    job_type: Optional[str] = None,
    work_mode: Optional[str] = None,
    experience_level: Optional[str] = None,
    salary_min: Optional[float] = None,
    salary_max: Optional[float] = None,
    is_featured: Optional[bool] = None,
    is_urgent: Optional[bool] = None,
    company_id: Optional[str] = None,
    status: str = "active",
):
    filters = [Job.status == JobStatus.ACTIVE]

    if q:
        search = f"%{q.lower()}%"
        filters.append(or_(
            func.lower(Job.title).like(search),
            func.lower(Job.description).like(search),
            func.lower(Job.category).like(search),
        ))
    if city:
        filters.append(func.lower(Job.city) == city.lower())
    if category:
        filters.append(func.lower(Job.category) == category.lower())
    if job_type:
        filters.append(Job.job_type == job_type)
    if work_mode:
        filters.append(Job.work_mode == work_mode)
    if experience_level:
        filters.append(Job.experience_level == experience_level)
    if salary_min is not None:
        filters.append(Job.salary_min_lpa >= salary_min)
    if salary_max is not None:
        filters.append(Job.salary_max_lpa <= salary_max)
    if is_featured is not None:
        filters.append(Job.is_featured == is_featured)
    if is_urgent is not None:
        filters.append(Job.is_urgent == is_urgent)
    if company_id:
        filters.append(Job.company_id == company_id)

    return and_(*filters)


@router.get("/", response_model=PaginatedResponse)
async def search_jobs(
    q: Optional[str] = Query(None, description="Keyword search"),
    city: Optional[str] = None,
    category: Optional[str] = None,
    job_type: Optional[str] = None,
    work_mode: Optional[str] = None,
    experience_level: Optional[str] = None,
    salary_min: Optional[float] = None,
    salary_max: Optional[float] = None,
    is_featured: Optional[bool] = None,
    is_urgent: Optional[bool] = None,
    company_id: Optional[str] = None,
    sort_by: str = Query("created_at", enum=["created_at", "salary_min_lpa", "applications_count"]),
    sort_order: str = Query("desc", enum=["asc", "desc"]),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    filters = build_job_query(q, city, category, job_type, work_mode, experience_level,
                               salary_min, salary_max, is_featured, is_urgent, company_id)

    # Count
    count_q = await db.execute(select(func.count()).select_from(Job).where(filters))
    total = count_q.scalar()

    # Sort
    sort_col = getattr(Job, sort_by, Job.created_at)
    order = sort_col.desc() if sort_order == "desc" else sort_col.asc()

    # Fetch with company eager-loaded
    result = await db.execute(
        select(Job)
        .options(selectinload(Job.company))
        .where(filters)
        .order_by(Job.is_featured.desc(), order)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    jobs = result.scalars().all()

    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        pages=-(-total // page_size),  # ceiling division
        items=[JobListResponse.model_validate(j) for j in jobs],
    )


@router.get("/featured", response_model=List[JobListResponse])
async def featured_jobs(limit: int = 6, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Job)
        .options(selectinload(Job.company))
        .where(Job.status == JobStatus.ACTIVE, Job.is_featured == True)
        .order_by(Job.published_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Job).options(selectinload(Job.company)).where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Increment view count
    job.views_count += 1
    return job


@router.get("/slug/{slug}", response_model=JobResponse)
async def get_job_by_slug(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Job).options(selectinload(Job.company)).where(Job.slug == slug)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.views_count += 1
    return job


@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    payload: JobCreateRequest,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    company = current_user.company
    if not company:
        raise HTTPException(status_code=400, detail="Create a company profile before posting jobs")

    job_id = str(uuid.uuid4())
    slug = slugify_job(payload.title, job_id)

    job = Job(
        id=job_id,
        company_id=company.id,
        posted_by_id=current_user.id,
        slug=slug,
        published_at=datetime.now(timezone.utc) if payload.status == JobStatus.ACTIVE else None,
        **payload.model_dump(),
    )
    db.add(job)
    await db.flush()

    # Reload with company
    await db.refresh(job)
    result = await db.execute(
        select(Job).options(selectinload(Job.company)).where(Job.id == job.id)
    )
    return result.scalar_one()


@router.patch("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: str,
    payload: JobUpdateRequest,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Job).options(selectinload(Job.company)).where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.company_id != current_user.company.id:
        raise HTTPException(status_code=403, detail="Not your job listing")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(job, field, value)

    if payload.status == JobStatus.ACTIVE and not job.published_at:
        job.published_at = datetime.now(timezone.utc)

    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.company_id != current_user.company.id:
        raise HTTPException(status_code=403, detail="Not your job listing")
    await db.delete(job)


@router.get("/employer/my-jobs", response_model=List[JobListResponse])
async def my_jobs(
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.company:
        return []
    result = await db.execute(
        select(Job)
        .options(selectinload(Job.company))
        .where(Job.company_id == current_user.company.id)
        .order_by(Job.created_at.desc())
    )
    return result.scalars().all()
