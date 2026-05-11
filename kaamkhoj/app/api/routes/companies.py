from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import re

from app.db.session import get_db
from app.models.models import User, Company
from app.schemas.schemas import CompanyCreateRequest, CompanyUpdateRequest, CompanyResponse
from app.api.deps import get_current_user, get_current_employer, get_current_admin
from app.api.routes.users import save_upload

router = APIRouter(prefix="/companies", tags=["Companies"])


def slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s]+", "-", s)
    return s


@router.post("/", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    payload: CompanyCreateRequest,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    if current_user.company:
        raise HTTPException(status_code=409, detail="You already have a company profile")

    base_slug = slugify(payload.name)
    # Ensure unique slug
    slug = base_slug
    counter = 1
    while True:
        existing = await db.execute(select(Company).where(Company.slug == slug))
        if not existing.scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    company = Company(owner_id=current_user.id, slug=slug, **payload.model_dump())
    db.add(company)
    await db.flush()
    return company


@router.get("/", response_model=List[CompanyResponse])
async def list_companies(
    skip: int = 0,
    limit: int = 20,
    industry: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Company)
    if industry:
        query = query.where(Company.industry == industry)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/me", response_model=CompanyResponse)
async def get_my_company(
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.company:
        raise HTTPException(status_code=404, detail="No company profile found. Please create one.")
    return current_user.company


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(company_id: str, db: AsyncSession = Depends(get_db)):
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.patch("/me", response_model=CompanyResponse)
async def update_company(
    payload: CompanyUpdateRequest,
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    company = current_user.company
    if not company:
        raise HTTPException(status_code=404, detail="No company profile found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "name" and value:
            company.slug = slugify(value)
        setattr(company, field, value)
    return company


@router.post("/me/logo", response_model=CompanyResponse)
async def upload_logo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    company = current_user.company
    if not company:
        raise HTTPException(status_code=404, detail="No company profile found")
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, or WebP images are allowed")

    url = save_upload(file, "company-logos")
    company.logo_url = url
    return company


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
    current_user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    company = current_user.company
    if not company:
        raise HTTPException(status_code=404, detail="No company profile found")
    await db.delete(company)


@router.patch("/{company_id}/verify", response_model=CompanyResponse)
async def verify_company(
    company_id: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    company.is_verified = True
    return company
