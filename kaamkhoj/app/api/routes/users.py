from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List
import os, uuid, shutil

from app.db.session import get_db
from app.models.models import User, SavedJob, Job
from app.schemas.schemas import UserResponse, UserUpdateRequest, JobListResponse
from app.api.deps import get_current_user, get_current_admin
from app.core.config import settings

router = APIRouter(prefix="/users", tags=["Users"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_RESUME_TYPES = {"application/pdf"}


def save_upload(file: UploadFile, folder: str) -> str:
    os.makedirs(f"{settings.UPLOAD_DIR}/{folder}", exist_ok=True)
    ext = file.filename.rsplit(".", 1)[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    path = f"{settings.UPLOAD_DIR}/{folder}/{filename}"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return f"/{path}"


@router.get("/me", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    payload: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)

    # Mark profile complete if key fields filled
    if all([current_user.bio, current_user.city, current_user.skills, current_user.experience_years]):
        current_user.is_profile_complete = True

    return current_user


@router.post("/me/avatar", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, or WebP images are allowed")
    if file.size and file.size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File must be under {settings.MAX_UPLOAD_SIZE_MB}MB")

    url = save_upload(file, "avatars")
    current_user.avatar_url = url
    return current_user


@router.post("/me/resume", response_model=UserResponse)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in ALLOWED_RESUME_TYPES:
        raise HTTPException(status_code=400, detail="Only PDF resumes are accepted")
    if file.size and file.size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File must be under {settings.MAX_UPLOAD_SIZE_MB}MB")

    url = save_upload(file, "resumes")
    current_user.resume_url = url
    return current_user


# ── Saved Jobs ───────────────────────────────────────────────────────────────

@router.get("/me/saved-jobs", response_model=List[JobListResponse])
async def get_saved_jobs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Job)
        .join(SavedJob, SavedJob.job_id == Job.id)
        .where(SavedJob.user_id == current_user.id)
    )
    return result.scalars().all()


@router.post("/me/saved-jobs/{job_id}", status_code=status.HTTP_201_CREATED)
async def save_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Check job exists
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check already saved
    existing = await db.execute(
        select(SavedJob).where(SavedJob.user_id == current_user.id, SavedJob.job_id == job_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Job already saved")

    db.add(SavedJob(user_id=current_user.id, job_id=job_id))
    return {"message": "Job saved successfully"}


@router.delete("/me/saved-jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unsave_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SavedJob).where(SavedJob.user_id == current_user.id, SavedJob.job_id == job_id)
    )
    saved = result.scalar_one_or_none()
    if not saved:
        raise HTTPException(status_code=404, detail="Saved job not found")
    await db.delete(saved)


# ── Admin: list all users ────────────────────────────────────────────────────

@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 50,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).offset(skip).limit(limit))
    return result.scalars().all()


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(user)
