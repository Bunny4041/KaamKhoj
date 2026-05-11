from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import Optional

from app.db.session import get_db
from app.models.models import Job, Company, JobStatus
from app.schemas.schemas import JobListResponse, CompanyResponse, PaginatedResponse

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/jobs", response_model=PaginatedResponse)
async def search_jobs(
    q: str = Query(..., min_length=1, description="Search keyword"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Full-text search across job titles, descriptions, skills, and company names."""
    keyword = f"%{q.lower()}%"

    condition = (
        Job.status == JobStatus.ACTIVE,
        or_(
            func.lower(Job.title).like(keyword),
            func.lower(Job.description).like(keyword),
            func.lower(Job.category).like(keyword),
            func.lower(Job.city).like(keyword),
        )
    )

    from sqlalchemy import and_
    where = and_(*condition)

    count_r = await db.execute(select(func.count()).select_from(Job).where(where))
    total = count_r.scalar()

    result = await db.execute(
        select(Job)
        .options(selectinload(Job.company))
        .where(where)
        .order_by(Job.is_featured.desc(), Job.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    jobs = result.scalars().all()

    return PaginatedResponse(
        total=total, page=page, page_size=page_size,
        pages=-(-total // page_size),
        items=[JobListResponse.model_validate(j) for j in jobs],
    )


@router.get("/companies", response_model=PaginatedResponse)
async def search_companies(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    keyword = f"%{q.lower()}%"
    condition = or_(
        func.lower(Company.name).like(keyword),
        func.lower(Company.description).like(keyword),
        func.lower(Company.industry).like(keyword),
    )

    count_r = await db.execute(select(func.count()).select_from(Company).where(condition))
    total = count_r.scalar()

    result = await db.execute(
        select(Company)
        .where(condition)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    companies = result.scalars().all()

    return PaginatedResponse(
        total=total, page=page, page_size=page_size,
        pages=-(-total // page_size),
        items=[CompanyResponse.model_validate(c) for c in companies],
    )


@router.get("/suggestions")
async def autocomplete(
    q: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
):
    """Returns autocomplete suggestions for job titles and cities."""
    keyword = f"%{q.lower()}%"

    titles_r = await db.execute(
        select(Job.title).where(
            Job.status == JobStatus.ACTIVE,
            func.lower(Job.title).like(keyword)
        ).distinct().limit(5)
    )
    titles = [r[0] for r in titles_r.fetchall()]

    cities_r = await db.execute(
        select(Job.city).where(
            Job.city.isnot(None),
            func.lower(Job.city).like(keyword)
        ).distinct().limit(5)
    )
    cities = [r[0] for r in cities_r.fetchall()]

    return {"titles": titles, "cities": cities}
