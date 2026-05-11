"""
KaamKhoj Backend — FastAPI Application
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
import os
import time

from app.core.config import settings
from app.db.session import create_tables
from app.api.routes import auth, users, companies, jobs, applications, notifications, search

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 KaamKhoj API starting up...")
    await create_tables()
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    logger.info("✅ Database tables ready")
    yield
    # Shutdown
    logger.info("👋 KaamKhoj API shutting down")


app = FastAPI(
    title="KaamKhoj API",
    description="""
## 🪷 KaamKhoj — India's Premier Job Board API

### Features
- **Auth** — Register, login, JWT refresh, email verification, password reset
- **Jobs** — Post, search, filter, full-text search with pagination
- **Applications** — Apply, track status, employer pipeline management
- **Companies** — Employer profiles, logo upload, verification
- **Notifications** — In-app notification feed, unread counts
- **Job Alerts** — Personalised alerts with daily/weekly frequency
- **Search** — Global search with autocomplete suggestions

### Authentication
Use `Bearer <access_token>` in the `Authorization` header.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request timing middleware ─────────────────────────────────────────────────
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start
    response.headers["X-Process-Time"] = f"{duration:.4f}s"
    return response


# ── Global exception handler ─────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please try again later."},
    )


# ── Static files (uploads) ───────────────────────────────────────────────────
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


# ── Routers ──────────────────────────────────────────────────────────────────
PREFIX = settings.API_V1_STR

app.include_router(auth.router,          prefix=PREFIX)
app.include_router(users.router,         prefix=PREFIX)
app.include_router(companies.router,     prefix=PREFIX)
app.include_router(jobs.router,          prefix=PREFIX)
app.include_router(applications.router,  prefix=PREFIX)
app.include_router(notifications.router, prefix=PREFIX)
app.include_router(search.router,        prefix=PREFIX)


# ── Health & Info ─────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
async def root():
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy", "environment": settings.APP_ENV}
