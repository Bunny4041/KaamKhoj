"""
Pydantic v2 schemas — request/response models for all endpoints.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from typing import Optional, List, Any
from datetime import datetime
import re

from app.models.models import (
    UserRole, JobType, WorkMode, JobStatus,
    ApplicationStatus, ExperienceLevel, NotificationType
)


# ── Shared ───────────────────────────────────────────────────────────────────

class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int
    items: List[Any]


# ── Auth ─────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    full_name: str = Field(min_length=2, max_length=255)
    role: UserRole = UserRole.JOBSEEKER
    phone: Optional[str] = None

    @field_validator("password")
    @classmethod
    def strong_password(cls, v):
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one digit")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        if v and not re.match(r"^[6-9]\d{9}$", v):
            raise ValueError("Enter a valid 10-digit Indian mobile number")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    role: UserRole


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


# ── User / Profile ────────────────────────────────────────────────────────────

class UserBase(BaseModel):
    full_name: str
    phone: Optional[str] = None
    bio: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    skills: Optional[List[str]] = []
    experience_years: Optional[int] = None
    current_ctc_lpa: Optional[float] = None
    expected_ctc_lpa: Optional[float] = None
    notice_period_days: Optional[int] = None


class UserUpdateRequest(UserBase):
    pass


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    phone: Optional[str]
    role: UserRole
    avatar_url: Optional[str]
    bio: Optional[str]
    city: Optional[str]
    state: Optional[str]
    linkedin_url: Optional[str]
    github_url: Optional[str]
    portfolio_url: Optional[str]
    resume_url: Optional[str]
    skills: Optional[List[str]]
    experience_years: Optional[int]
    current_ctc_lpa: Optional[float]
    expected_ctc_lpa: Optional[float]
    notice_period_days: Optional[int]
    is_active: bool
    is_verified: bool
    is_profile_complete: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserPublicResponse(BaseModel):
    """Minimal profile for public views."""
    id: str
    full_name: str
    avatar_url: Optional[str]
    city: Optional[str]
    skills: Optional[List[str]]
    experience_years: Optional[int]

    model_config = {"from_attributes": True}


# ── Company ───────────────────────────────────────────────────────────────────

class CompanyCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    website: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    founded_year: Optional[int] = None
    headquarters: Optional[str] = None
    linkedin_url: Optional[str] = None
    gstin: Optional[str] = None


class CompanyUpdateRequest(CompanyCreateRequest):
    name: Optional[str] = None


class CompanyResponse(BaseModel):
    id: str
    name: str
    slug: str
    logo_url: Optional[str]
    banner_url: Optional[str]
    website: Optional[str]
    description: Optional[str]
    industry: Optional[str]
    company_size: Optional[str]
    founded_year: Optional[int]
    headquarters: Optional[str]
    linkedin_url: Optional[str]
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Job ───────────────────────────────────────────────────────────────────────

class JobCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=50)
    responsibilities: Optional[List[str]] = []
    requirements: Optional[List[str]] = []
    nice_to_have: Optional[List[str]] = []
    job_type: JobType = JobType.FULL_TIME
    work_mode: WorkMode = WorkMode.ON_SITE
    experience_level: ExperienceLevel = ExperienceLevel.MID
    experience_min_years: Optional[int] = None
    experience_max_years: Optional[int] = None
    category: Optional[str] = None
    skills_required: Optional[List[str]] = []
    city: Optional[str] = None
    state: Optional[str] = None
    salary_min_lpa: Optional[float] = None
    salary_max_lpa: Optional[float] = None
    salary_is_disclosed: bool = True
    is_featured: bool = False
    is_urgent: bool = False
    application_deadline: Optional[datetime] = None
    status: JobStatus = JobStatus.ACTIVE

    @model_validator(mode="after")
    def validate_salary(self):
        if self.salary_min_lpa and self.salary_max_lpa:
            if self.salary_min_lpa > self.salary_max_lpa:
                raise ValueError("salary_min_lpa must be <= salary_max_lpa")
        return self


class JobUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    responsibilities: Optional[List[str]] = None
    requirements: Optional[List[str]] = None
    nice_to_have: Optional[List[str]] = None
    job_type: Optional[JobType] = None
    work_mode: Optional[WorkMode] = None
    experience_level: Optional[ExperienceLevel] = None
    experience_min_years: Optional[int] = None
    experience_max_years: Optional[int] = None
    category: Optional[str] = None
    skills_required: Optional[List[str]] = None
    city: Optional[str] = None
    state: Optional[str] = None
    salary_min_lpa: Optional[float] = None
    salary_max_lpa: Optional[float] = None
    salary_is_disclosed: Optional[bool] = None
    is_featured: Optional[bool] = None
    is_urgent: Optional[bool] = None
    application_deadline: Optional[datetime] = None
    status: Optional[JobStatus] = None


class JobResponse(BaseModel):
    id: str
    title: str
    slug: str
    description: str
    responsibilities: Optional[List[str]]
    requirements: Optional[List[str]]
    nice_to_have: Optional[List[str]]
    job_type: JobType
    work_mode: WorkMode
    experience_level: ExperienceLevel
    experience_min_years: Optional[int]
    experience_max_years: Optional[int]
    category: Optional[str]
    skills_required: Optional[List[str]]
    city: Optional[str]
    state: Optional[str]
    country: str
    salary_min_lpa: Optional[float]
    salary_max_lpa: Optional[float]
    salary_is_disclosed: bool
    status: JobStatus
    is_featured: bool
    is_urgent: bool
    application_deadline: Optional[datetime]
    views_count: int
    applications_count: int
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]
    company: Optional[CompanyResponse]

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    """Lighter version for list views."""
    id: str
    title: str
    slug: str
    job_type: JobType
    work_mode: WorkMode
    experience_level: ExperienceLevel
    city: Optional[str]
    salary_min_lpa: Optional[float]
    salary_max_lpa: Optional[float]
    salary_is_disclosed: bool
    is_featured: bool
    is_urgent: bool
    applications_count: int
    created_at: datetime
    company: Optional[CompanyResponse]

    model_config = {"from_attributes": True}


# ── Application ───────────────────────────────────────────────────────────────

class ApplicationCreateRequest(BaseModel):
    cover_letter: Optional[str] = None
    expected_ctc_lpa: Optional[float] = None
    notice_period_days: Optional[int] = None


class ApplicationStatusUpdateRequest(BaseModel):
    status: ApplicationStatus
    employer_notes: Optional[str] = None
    interview_date: Optional[datetime] = None
    interview_link: Optional[str] = None
    rejection_reason: Optional[str] = None


class ApplicationResponse(BaseModel):
    id: str
    status: ApplicationStatus
    cover_letter: Optional[str]
    resume_url: Optional[str]
    expected_ctc_lpa: Optional[float]
    notice_period_days: Optional[int]
    employer_notes: Optional[str]
    interview_date: Optional[datetime]
    interview_link: Optional[str]
    rejection_reason: Optional[str]
    created_at: datetime
    updated_at: datetime
    job: Optional[JobListResponse]
    applicant: Optional[UserPublicResponse]

    model_config = {"from_attributes": True}


# ── Notification ──────────────────────────────────────────────────────────────

class NotificationResponse(BaseModel):
    id: str
    type: NotificationType
    title: str
    message: str
    is_read: bool
    action_url: Optional[str]
    meta: Optional[dict]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Job Alert ─────────────────────────────────────────────────────────────────

class JobAlertCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    keywords: Optional[List[str]] = []
    cities: Optional[List[str]] = []
    categories: Optional[List[str]] = []
    job_types: Optional[List[str]] = []
    work_modes: Optional[List[str]] = []
    salary_min_lpa: Optional[float] = None
    experience_level: Optional[str] = None
    frequency: str = "daily"


class JobAlertResponse(BaseModel):
    id: str
    name: str
    keywords: Optional[List[str]]
    cities: Optional[List[str]]
    categories: Optional[List[str]]
    frequency: str
    is_active: bool
    last_sent_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Search ────────────────────────────────────────────────────────────────────

class JobSearchParams(BaseModel):
    q: Optional[str] = None           # Full-text keyword
    city: Optional[str] = None
    category: Optional[str] = None
    job_type: Optional[JobType] = None
    work_mode: Optional[WorkMode] = None
    experience_level: Optional[ExperienceLevel] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    is_featured: Optional[bool] = None
    is_urgent: Optional[bool] = None
    company_id: Optional[str] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    sort_by: str = "created_at"       # created_at | salary | relevance
    sort_order: str = "desc"          # asc | desc
