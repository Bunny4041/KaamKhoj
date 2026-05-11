"""
KaamKhoj — Database Models
All tables defined here with relationships.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    String, Text, Boolean, Integer, Float, DateTime, Enum,
    ForeignKey, Index, JSON, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.session import Base


def utcnow():
    return datetime.now(timezone.utc)


def gen_uuid():
    return str(uuid.uuid4())


# ── Enums ────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    JOBSEEKER = "jobseeker"
    EMPLOYER  = "employer"
    ADMIN     = "admin"


class JobType(str, enum.Enum):
    FULL_TIME  = "full_time"
    PART_TIME  = "part_time"
    CONTRACT   = "contract"
    INTERNSHIP = "internship"
    FREELANCE  = "freelance"


class WorkMode(str, enum.Enum):
    REMOTE  = "remote"
    HYBRID  = "hybrid"
    ON_SITE = "on_site"


class JobStatus(str, enum.Enum):
    DRAFT     = "draft"
    ACTIVE    = "active"
    PAUSED    = "paused"
    CLOSED    = "closed"
    EXPIRED   = "expired"


class ApplicationStatus(str, enum.Enum):
    APPLIED    = "applied"
    REVIEWING  = "reviewing"
    SHORTLISTED = "shortlisted"
    INTERVIEW  = "interview"
    OFFERED    = "offered"
    REJECTED   = "rejected"
    WITHDRAWN  = "withdrawn"


class ExperienceLevel(str, enum.Enum):
    FRESHER    = "fresher"
    JUNIOR     = "junior"
    MID        = "mid"
    SENIOR     = "senior"
    LEAD       = "lead"
    MANAGER    = "manager"
    DIRECTOR   = "director"


class NotificationType(str, enum.Enum):
    APPLICATION_RECEIVED  = "application_received"
    APPLICATION_STATUS    = "application_status"
    JOB_ALERT            = "job_alert"
    PROFILE_VIEW         = "profile_view"
    MESSAGE              = "message"
    SYSTEM               = "system"


# ── Models ───────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.JOBSEEKER)

    # Profile
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))
    bio: Mapped[Optional[str]] = mapped_column(Text)
    city: Mapped[Optional[str]] = mapped_column(String(100))
    state: Mapped[Optional[str]] = mapped_column(String(100))
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500))
    github_url: Mapped[Optional[str]] = mapped_column(String(500))
    portfolio_url: Mapped[Optional[str]] = mapped_column(String(500))
    resume_url: Mapped[Optional[str]] = mapped_column(String(500))
    skills: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    experience_years: Mapped[Optional[int]] = mapped_column(Integer)
    current_ctc_lpa: Mapped[Optional[float]] = mapped_column(Float)
    expected_ctc_lpa: Mapped[Optional[float]] = mapped_column(Float)
    notice_period_days: Mapped[Optional[int]] = mapped_column(Integer)

    # Account
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_profile_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    company: Mapped[Optional["Company"]] = relationship("Company", back_populates="owner", uselist=False)
    applications: Mapped[List["Application"]] = relationship("Application", back_populates="applicant", cascade="all, delete-orphan")
    saved_jobs: Mapped[List["SavedJob"]] = relationship("SavedJob", back_populates="user", cascade="all, delete-orphan")
    notifications: Mapped[List["Notification"]] = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    job_alerts: Mapped[List["JobAlert"]] = relationship("JobAlert", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_users_email_role", "email", "role"),
    )


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    owner_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500))
    banner_url: Mapped[Optional[str]] = mapped_column(String(500))
    website: Mapped[Optional[str]] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text)
    industry: Mapped[Optional[str]] = mapped_column(String(100))
    company_size: Mapped[Optional[str]] = mapped_column(String(50))  # e.g. "11-50"
    founded_year: Mapped[Optional[int]] = mapped_column(Integer)
    headquarters: Mapped[Optional[str]] = mapped_column(String(200))
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500))
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    gstin: Mapped[Optional[str]] = mapped_column(String(20))  # India GST number
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    owner: Mapped["User"] = relationship("User", back_populates="company")
    jobs: Mapped[List["Job"]] = relationship("Job", back_populates="company", cascade="all, delete-orphan")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    company_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("companies.id", ondelete="CASCADE"))
    posted_by_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"))

    # Core
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(300), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    responsibilities: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    requirements: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    nice_to_have: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    # Classification
    job_type: Mapped[JobType] = mapped_column(Enum(JobType), default=JobType.FULL_TIME)
    work_mode: Mapped[WorkMode] = mapped_column(Enum(WorkMode), default=WorkMode.ON_SITE)
    experience_level: Mapped[ExperienceLevel] = mapped_column(Enum(ExperienceLevel), default=ExperienceLevel.MID)
    experience_min_years: Mapped[Optional[int]] = mapped_column(Integer)
    experience_max_years: Mapped[Optional[int]] = mapped_column(Integer)
    category: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    skills_required: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    # Location
    city: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    state: Mapped[Optional[str]] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(String(100), default="India")

    # Compensation (in INR LPA)
    salary_min_lpa: Mapped[Optional[float]] = mapped_column(Float)
    salary_max_lpa: Mapped[Optional[float]] = mapped_column(Float)
    salary_is_disclosed: Mapped[bool] = mapped_column(Boolean, default=True)

    # Status & Meta
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.DRAFT, index=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    is_urgent: Mapped[bool] = mapped_column(Boolean, default=False)
    application_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    views_count: Mapped[int] = mapped_column(Integer, default=0)
    applications_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    company: Mapped["Company"] = relationship("Company", back_populates="jobs")
    applications: Mapped[List["Application"]] = relationship("Application", back_populates="job", cascade="all, delete-orphan")
    saved_by: Mapped[List["SavedJob"]] = relationship("SavedJob", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_jobs_status_featured", "status", "is_featured"),
        Index("ix_jobs_city_category", "city", "category"),
        Index("ix_jobs_created_at", "created_at"),
    )


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    job_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("jobs.id", ondelete="CASCADE"))
    applicant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"))
    status: Mapped[ApplicationStatus] = mapped_column(Enum(ApplicationStatus), default=ApplicationStatus.APPLIED, index=True)

    # Submission
    cover_letter: Mapped[Optional[str]] = mapped_column(Text)
    resume_url: Mapped[Optional[str]] = mapped_column(String(500))  # snapshot at apply time
    expected_ctc_lpa: Mapped[Optional[float]] = mapped_column(Float)
    notice_period_days: Mapped[Optional[int]] = mapped_column(Integer)

    # Employer notes
    employer_notes: Mapped[Optional[str]] = mapped_column(Text)
    interview_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    interview_link: Mapped[Optional[str]] = mapped_column(String(500))
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    applicant: Mapped["User"] = relationship("User", back_populates="applications")
    job: Mapped["Job"] = relationship("Job", back_populates="applications")

    __table_args__ = (
        Index("ix_applications_job_applicant", "job_id", "applicant_id", unique=True),
        Index("ix_applications_status", "status"),
    )


class SavedJob(Base):
    __tablename__ = "saved_jobs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"))
    job_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("jobs.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship("User", back_populates="saved_jobs")
    job: Mapped["Job"] = relationship("Job", back_populates="saved_by")

    __table_args__ = (
        Index("ix_saved_jobs_unique", "user_id", "job_id", unique=True),
    )


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType))
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    action_url: Mapped[Optional[str]] = mapped_column(String(500))
    meta: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship("User", back_populates="notifications")


class JobAlert(Base):
    __tablename__ = "job_alerts"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))

    # Filter criteria (stored as JSON)
    keywords: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    cities: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    categories: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    job_types: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    work_modes: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    salary_min_lpa: Mapped[Optional[float]] = mapped_column(Float)
    experience_level: Mapped[Optional[str]] = mapped_column(String(50))

    frequency: Mapped[str] = mapped_column(String(20), default="daily")  # daily | weekly
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship("User", back_populates="job_alerts")
