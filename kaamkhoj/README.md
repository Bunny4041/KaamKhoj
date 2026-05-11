# 🪷 KaamKhoj — Backend API

**India's premier job board** — Full-featured REST API built with FastAPI + PostgreSQL.

---

## 🏗️ Architecture

```
kaamkhoj/
├── app/
│   ├── main.py                  # FastAPI app, middleware, router registration
│   ├── api/
│   │   ├── deps.py              # Auth dependencies (get_current_user etc.)
│   │   └── routes/
│   │       ├── auth.py          # Register, login, JWT refresh, email verify
│   │       ├── users.py         # Profile, avatar, resume upload, saved jobs
│   │       ├── companies.py     # Employer company profiles
│   │       ├── jobs.py          # Job CRUD + search + filters
│   │       ├── applications.py  # Apply, track, pipeline management
│   │       ├── notifications.py # In-app notifications + job alerts
│   │       └── search.py        # Full-text search + autocomplete
│   ├── core/
│   │   ├── config.py            # Pydantic settings (env-driven)
│   │   └── security.py          # JWT, password hashing
│   ├── db/
│   │   └── session.py           # Async SQLAlchemy engine + session
│   ├── models/
│   │   └── models.py            # All ORM models (User, Job, Company, ...)
│   ├── schemas/
│   │   └── schemas.py           # Pydantic v2 request/response schemas
│   └── services/
│       └── notification_service.py  # Notification + email helpers
├── tests/
│   └── test_api.py              # Pytest async test suite
├── alembic/                     # DB migrations
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## ⚡ Tech Stack

| Layer        | Technology                        |
|--------------|-----------------------------------|
| Framework    | FastAPI 0.111                     |
| Language     | Python 3.12                       |
| Database     | PostgreSQL 16                     |
| ORM          | SQLAlchemy 2.0 (async)            |
| Migrations   | Alembic                           |
| Auth         | JWT (python-jose) + bcrypt        |
| Cache/Queue  | Redis                             |
| Validation   | Pydantic v2                       |
| Testing      | Pytest + pytest-asyncio + httpx   |
| Container    | Docker + Docker Compose           |

---

## 🚀 Quick Start

### Option A — Docker Compose (Recommended)

```bash
# 1. Clone and enter project
cd kaamkhoj

# 2. Copy env file
cp .env.example .env

# 3. Start everything (PostgreSQL + Redis + API)
docker-compose up --build

# API is live at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

### Option B — Local Development

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your PostgreSQL credentials

# 4. Run database migrations
alembic upgrade head

# 5. Start the server
uvicorn app.main:app --reload --port 8000
```

---

## 🔑 Environment Variables

| Variable                    | Description                          | Default                    |
|-----------------------------|--------------------------------------|----------------------------|
| `DATABASE_URL`              | Async PostgreSQL URL                 | `postgresql+asyncpg://...` |
| `SYNC_DATABASE_URL`         | Sync PostgreSQL URL (Alembic)        | `postgresql://...`         |
| `SECRET_KEY`                | JWT signing secret (min 32 chars)    | **Change this!**           |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token TTL                   | `30`                       |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token TTL                    | `7`                        |
| `REDIS_URL`                 | Redis connection URL                 | `redis://localhost:6379/0` |
| `SMTP_HOST`                 | SMTP server for emails               | `smtp.gmail.com`           |
| `SMTP_USER`                 | SMTP username                        | —                          |
| `SMTP_PASSWORD`             | SMTP password / app password         | —                          |
| `EMAILS_ENABLED`            | Toggle email sending                 | `false`                    |
| `FRONTEND_URL`              | Frontend URL (for email links, CORS) | `http://localhost:3000`    |
| `UPLOAD_DIR`                | Directory for file uploads           | `uploads`                  |
| `MAX_UPLOAD_SIZE_MB`        | Max file size for uploads            | `5`                        |

---

## 📡 API Reference

Base URL: `http://localhost:8000/api/v1`
Interactive docs: `http://localhost:8000/docs`

### 🔐 Auth
| Method | Endpoint                    | Description                     | Auth |
|--------|-----------------------------|---------------------------------|------|
| POST   | `/auth/register`            | Register (jobseeker or employer)| ❌   |
| POST   | `/auth/login`               | Login → access + refresh tokens | ❌   |
| POST   | `/auth/refresh`             | Refresh access token            | ❌   |
| GET    | `/auth/verify-email`        | Verify email via token          | ❌   |
| POST   | `/auth/forgot-password`     | Send password reset email       | ❌   |
| POST   | `/auth/reset-password`      | Confirm password reset          | ❌   |
| POST   | `/auth/change-password`     | Change password (logged in)     | ✅   |
| GET    | `/auth/me`                  | Get current user                | ✅   |

### 👤 Users
| Method | Endpoint                    | Description                     | Auth     |
|--------|-----------------------------|---------------------------------|----------|
| GET    | `/users/me`                 | Get own profile                 | ✅       |
| PATCH  | `/users/me`                 | Update profile                  | ✅       |
| POST   | `/users/me/avatar`          | Upload profile photo (JPEG/PNG) | ✅       |
| POST   | `/users/me/resume`          | Upload resume (PDF only)        | ✅       |
| GET    | `/users/me/saved-jobs`      | List saved jobs                 | ✅       |
| POST   | `/users/me/saved-jobs/{id}` | Save a job                      | ✅       |
| DELETE | `/users/me/saved-jobs/{id}` | Remove saved job                | ✅       |
| GET    | `/users/`                   | List all users (admin only)     | 🛡️ Admin |
| DELETE | `/users/{id}`               | Delete user (admin only)        | 🛡️ Admin |

### 🏢 Companies
| Method | Endpoint                    | Description                     | Auth       |
|--------|-----------------------------|---------------------------------|------------|
| POST   | `/companies/`               | Create company profile          | 🏭 Employer|
| GET    | `/companies/`               | List companies                  | ❌         |
| GET    | `/companies/me`             | Get own company                 | 🏭 Employer|
| PATCH  | `/companies/me`             | Update company                  | 🏭 Employer|
| POST   | `/companies/me/logo`        | Upload company logo             | 🏭 Employer|
| GET    | `/companies/{id}`           | Get company by ID               | ❌         |
| DELETE | `/companies/me`             | Delete company                  | 🏭 Employer|
| PATCH  | `/companies/{id}/verify`    | Verify company (admin only)     | 🛡️ Admin  |

### 💼 Jobs
| Method | Endpoint                    | Description                           | Auth       |
|--------|-----------------------------|---------------------------------------|------------|
| GET    | `/jobs/`                    | Search & filter jobs (paginated)      | ❌         |
| GET    | `/jobs/featured`            | Get featured jobs                     | ❌         |
| GET    | `/jobs/{id}`                | Get job by ID (increments views)      | ❌         |
| GET    | `/jobs/slug/{slug}`         | Get job by slug                       | ❌         |
| POST   | `/jobs/`                    | Create job listing                    | 🏭 Employer|
| PATCH  | `/jobs/{id}`                | Update job                            | 🏭 Employer|
| DELETE | `/jobs/{id}`                | Delete job                            | 🏭 Employer|
| GET    | `/jobs/employer/my-jobs`    | List employer's own jobs              | 🏭 Employer|

**Job search query params:**
`q`, `city`, `category`, `job_type`, `work_mode`, `experience_level`,
`salary_min`, `salary_max`, `is_featured`, `is_urgent`, `company_id`,
`sort_by` (created_at | salary_min_lpa | applications_count), `sort_order`, `page`, `page_size`

### 📋 Applications
| Method | Endpoint                              | Description                      | Auth       |
|--------|---------------------------------------|----------------------------------|------------|
| POST   | `/applications/{job_id}`             | Apply for a job                  | ✅ Seeker  |
| GET    | `/applications/me`                   | My applications (paginated)      | ✅         |
| GET    | `/applications/{id}`                 | Get application detail           | ✅         |
| PATCH  | `/applications/{id}/status`          | Update status (employer)         | 🏭 Employer|
| PATCH  | `/applications/{id}/withdraw`        | Withdraw application             | ✅ Seeker  |
| GET    | `/applications/job/{job_id}`         | All applicants for a job         | 🏭 Employer|

**Application statuses:** `applied → reviewing → shortlisted → interview → offered / rejected / withdrawn`

### 🔔 Notifications
| Method | Endpoint                              | Description                      | Auth |
|--------|---------------------------------------|----------------------------------|------|
| GET    | `/notifications`                     | List notifications (paginated)   | ✅   |
| GET    | `/notifications/unread-count`        | Get unread count                 | ✅   |
| PATCH  | `/notifications/{id}/read`           | Mark one as read                 | ✅   |
| PATCH  | `/notifications/mark-all-read`       | Mark all as read                 | ✅   |
| DELETE | `/notifications/{id}`                | Delete notification              | ✅   |

### 🚨 Job Alerts
| Method | Endpoint                    | Description                     | Auth |
|--------|-----------------------------|---------------------------------|------|
| GET    | `/alerts`                   | List my alerts                  | ✅   |
| POST   | `/alerts`                   | Create alert (max 10)           | ✅   |
| PATCH  | `/alerts/{id}`              | Update alert                    | ✅   |
| PATCH  | `/alerts/{id}/toggle`       | Enable / disable alert          | ✅   |
| DELETE | `/alerts/{id}`              | Delete alert                    | ✅   |

### 🔍 Search
| Method | Endpoint                    | Description                     | Auth |
|--------|-----------------------------|---------------------------------|------|
| GET    | `/search/jobs?q=...`        | Full-text job search            | ❌   |
| GET    | `/search/companies?q=...`   | Full-text company search        | ❌   |
| GET    | `/search/suggestions?q=...` | Autocomplete (titles + cities)  | ❌   |

---

## 🧪 Running Tests

```bash
# Install test dependencies (aiosqlite for in-memory DB)
pip install aiosqlite pytest-asyncio httpx

# Run full test suite
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=app --cov-report=term-missing
```

---

## 🗄️ Database Migrations (Alembic)

```bash
# Create a new migration after model changes
alembic revision --autogenerate -m "add salary field to jobs"

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

---

## 🛡️ Security Features

- **Passwords** hashed with bcrypt (cost factor 12)
- **JWT** access tokens (30 min) + refresh tokens (7 days)
- **Email verification** before sensitive actions
- **Role-based access control** — jobseeker / employer / admin
- **Email enumeration protection** on forgot-password
- **File type validation** on uploads (PDF for resumes, JPEG/PNG/WebP for images)
- **File size limits** (configurable, default 5 MB)
- **CORS** restricted to configured frontend URL
- **Non-root Docker user** for container security
- **Request timing header** (`X-Process-Time`) for observability

---

## 📬 Notification Triggers

| Event                        | Who gets notified |
|------------------------------|-------------------|
| New application received     | Employer          |
| Application status changed   | Job seeker        |
| Job alert match              | Job seeker        |

Email sending is stubbed (logged to console) by default. Set `EMAILS_ENABLED=true` and configure SMTP to enable real emails.

---

## 🗺️ Roadmap

- [ ] WebSocket real-time notifications
- [ ] Celery workers for scheduled job alerts (daily/weekly)
- [ ] PostgreSQL full-text search with `tsvector`
- [ ] Resume parsing with AI
- [ ] Admin dashboard endpoints
- [ ] Rate limiting with slowapi + Redis
- [ ] S3/CloudFront for file uploads
- [ ] Interview scheduling integration

---

*Built with ❤️ for Bharat — KaamKhoj Technologies Pvt Ltd*
