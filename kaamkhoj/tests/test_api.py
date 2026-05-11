"""
KaamKhoj — Test Suite
Run with: pytest tests/ -v
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.db.session import get_db, Base
from app.core.config import settings

# Use SQLite for tests (no PostgreSQL needed in CI)
TEST_DB_URL = "sqlite+aiosqlite:///./test_kaamkhoj.db"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestSession() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ── Helpers ───────────────────────────────────────────────────────────────────

async def register_user(client, email="test@example.com", password="Test1234", role="jobseeker"):
    return await client.post("/api/v1/auth/register", json={
        "email": email,
        "full_name": "Test User",
        "password": password,
        "role": role,
    })


async def login_user(client, email="test@example.com", password="Test1234"):
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return r.json()["access_token"]


async def get_auth_headers(client, email="test@example.com", password="Test1234", role="jobseeker"):
    await register_user(client, email, password, role)
    token = await login_user(client, email, password)
    return {"Authorization": f"Bearer {token}"}


# ── Auth Tests ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_success(client):
    r = await register_user(client)
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == "test@example.com"
    assert data["role"] == "jobseeker"
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    await register_user(client)
    r = await register_user(client)
    assert r.status_code == 400
    assert "already registered" in r.json()["detail"]


@pytest.mark.asyncio
async def test_register_weak_password(client):
    r = await register_user(client, password="weak")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client):
    await register_user(client)
    r = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "Test1234",
    })
    assert r.status_code == 200
    assert "access_token" in r.json()
    assert "refresh_token" in r.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await register_user(client)
    r = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "WrongPass99",
    })
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client):
    headers = await get_auth_headers(client)
    r = await client.get("/api/v1/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_refresh_token(client):
    await register_user(client)
    login_r = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com", "password": "Test1234"
    })
    refresh_token = login_r.json()["refresh_token"]
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert r.status_code == 200
    assert "access_token" in r.json()


# ── Profile Tests ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_profile(client):
    headers = await get_auth_headers(client)
    r = await client.patch("/api/v1/users/me", json={
        "bio": "Python developer from Bengaluru",
        "city": "Bengaluru",
        "skills": ["Python", "FastAPI", "PostgreSQL"],
        "experience_years": 3,
    }, headers=headers)
    assert r.status_code == 200
    assert r.json()["city"] == "Bengaluru"
    assert "Python" in r.json()["skills"]


# ── Job Tests ─────────────────────────────────────────────────────────────────

async def create_employer_with_company(client):
    """Sets up a verified employer with company."""
    headers = await get_auth_headers(client, "employer@example.com", "Test1234", "employer")

    # Create company
    await client.post("/api/v1/companies/", json={
        "name": "TechCorp India",
        "industry": "IT Software",
        "headquarters": "Bengaluru",
    }, headers=headers)

    return headers


@pytest.mark.asyncio
async def test_create_job(client):
    headers = await create_employer_with_company(client)
    r = await client.post("/api/v1/jobs/", json={
        "title": "Senior Python Developer",
        "description": "We are looking for a senior Python developer with FastAPI experience to join our growing team in Bengaluru.",
        "job_type": "full_time",
        "work_mode": "hybrid",
        "experience_level": "senior",
        "city": "Bengaluru",
        "salary_min_lpa": 20.0,
        "salary_max_lpa": 35.0,
        "skills_required": ["Python", "FastAPI", "PostgreSQL"],
        "status": "active",
    }, headers=headers)
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "Senior Python Developer"
    assert data["company"]["name"] == "TechCorp India"


@pytest.mark.asyncio
async def test_search_jobs(client):
    headers = await create_employer_with_company(client)
    await client.post("/api/v1/jobs/", json={
        "title": "Data Scientist",
        "description": "Looking for a data scientist with ML and Python experience for our Hyderabad office.",
        "job_type": "full_time",
        "work_mode": "on_site",
        "experience_level": "mid",
        "city": "Hyderabad",
        "status": "active",
    }, headers=headers)

    r = await client.get("/api/v1/jobs/?q=data+scientist")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    assert any("Data Scientist" in item["title"] for item in data["items"])


@pytest.mark.asyncio
async def test_jobseeker_cannot_post_job(client):
    headers = await get_auth_headers(client)
    r = await client.post("/api/v1/jobs/", json={
        "title": "Test Job",
        "description": "This should fail because the user is a jobseeker not an employer.",
        "job_type": "full_time",
        "work_mode": "remote",
        "experience_level": "junior",
        "status": "active",
    }, headers=headers)
    assert r.status_code == 403


# ── Application Tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_apply_for_job(client):
    emp_headers = await create_employer_with_company(client)
    job_r = await client.post("/api/v1/jobs/", json={
        "title": "Backend Engineer",
        "description": "Looking for backend engineer with Python and FastAPI skills for remote work.",
        "job_type": "full_time",
        "work_mode": "remote",
        "experience_level": "mid",
        "status": "active",
    }, headers=emp_headers)
    job_id = job_r.json()["id"]

    # Jobseeker applies
    seeker_headers = await get_auth_headers(client, "seeker@example.com", "Test1234", "jobseeker")
    r = await client.post(f"/api/v1/applications/{job_id}", json={
        "cover_letter": "I am very interested in this role.",
        "expected_ctc_lpa": 18.0,
    }, headers=seeker_headers)
    assert r.status_code == 201
    assert r.json()["status"] == "applied"


@pytest.mark.asyncio
async def test_duplicate_application(client):
    emp_headers = await create_employer_with_company(client)
    job_r = await client.post("/api/v1/jobs/", json={
        "title": "Frontend Dev",
        "description": "React developer needed for our product team in Mumbai office.",
        "job_type": "full_time",
        "work_mode": "on_site",
        "experience_level": "junior",
        "status": "active",
    }, headers=emp_headers)
    job_id = job_r.json()["id"]

    seeker_headers = await get_auth_headers(client, "seeker2@example.com", "Test1234", "jobseeker")
    await client.post(f"/api/v1/applications/{job_id}", json={}, headers=seeker_headers)
    r = await client.post(f"/api/v1/applications/{job_id}", json={}, headers=seeker_headers)
    assert r.status_code == 409


# ── Notification Tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_notifications_list(client):
    headers = await get_auth_headers(client)
    r = await client.get("/api/v1/notifications", headers=headers)
    assert r.status_code == 200
    assert "items" in r.json()


@pytest.mark.asyncio
async def test_unread_count(client):
    headers = await get_auth_headers(client)
    r = await client.get("/api/v1/notifications/unread-count", headers=headers)
    assert r.status_code == 200
    assert "unread_count" in r.json()


# ── Job Alert Tests ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_job_alert(client):
    headers = await get_auth_headers(client)
    r = await client.post("/api/v1/alerts", json={
        "name": "Python Jobs in Bengaluru",
        "keywords": ["Python", "FastAPI"],
        "cities": ["Bengaluru"],
        "frequency": "daily",
    }, headers=headers)
    assert r.status_code == 201
    assert r.json()["name"] == "Python Jobs in Bengaluru"


@pytest.mark.asyncio
async def test_health_endpoint(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"
