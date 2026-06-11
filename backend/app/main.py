from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from gspread.exceptions import APIError
from pathlib import Path


from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.classifications import router as classifications_router
from app.api.data_sources import router as data_sources_router
from app.api.dashboard import router as dashboard_router
from app.api.google_connection import router as google_connection_router
from app.api.google_oauth import router as google_oauth_router
from app.api.inquiry import router as inquiry_router
from app.api.settings import router as settings_router
from app.api.sync_jobs import router as sync_jobs_router
from app.api.workspace_invitations import router as workspace_invitations_router
from app.api.workspaces import router as workspaces_router
from app.config import settings
from app.database import check_database_connection, close_database_pool

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = PROJECT_ROOT / "apps" / "web" / "dist"
FRONTEND_INDEX = FRONTEND_DIST / "index.html"

app = FastAPI()


@app.exception_handler(APIError)
def handle_google_sheets_api_error(_request, exc):
    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", 500)

    if status_code == 429:
        return JSONResponse(
            status_code=429,
            content={
                "detail": (
                    "Kuota baca Google Sheets sedang habis. "
                    "Tunggu sekitar 1 menit, lalu coba lagi."
                )
            },
        )

    return JSONResponse(
        status_code=status_code,
        content={"detail": "Google Sheets API error."},
    )

# =========================
# CORS
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    if FRONTEND_INDEX.is_file():
        return FileResponse(FRONTEND_INDEX)

    return {
        "service": "finance-dashboard-api",
        "status": "ok",
        "health": "/api/health",
    }


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/health/db")
def database_health_check():
    result = check_database_connection()

    if result["ok"]:
        return {
            "status": "ok",
            "database": "connected",
        }

    return JSONResponse(
        status_code=503,
        content={
            "status": "error",
            "database": "unavailable",
            "message": "database connection failed",
        },
    )


@app.on_event("shutdown")
def shutdown_database_pool():
    close_database_pool()

# =========================
# ROUTER
# =========================
app.include_router(
    auth_router,
    prefix="/api/auth",
    tags=["Auth"]
)

app.include_router(
    auth_router,
    prefix="/auth",
    tags=["Auth"],
    include_in_schema=False,
)

app.include_router(
    dashboard_router,
    prefix="/api/dashboard",
    tags=["Dashboard"]
)

app.include_router(google_connection_router)
app.include_router(google_oauth_router)
app.include_router(data_sources_router)
app.include_router(sync_jobs_router)
app.include_router(classifications_router)
app.include_router(inquiry_router)
app.include_router(settings_router)
app.include_router(workspaces_router)
app.include_router(workspace_invitations_router)

app.include_router(admin_router)

if (FRONTEND_DIST / "assets").is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_DIST / "assets"),
        name="frontend-assets",
    )


@app.get("/{frontend_path:path}", include_in_schema=False)
def serve_frontend(frontend_path: str):
    if frontend_path.startswith("api/") or frontend_path == "api":
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    if not FRONTEND_INDEX.is_file():
        return JSONResponse(
            status_code=404,
            content={
                "detail": (
                    "Frontend build not found. Run npm run build:web before "
                    "serving SPA routes."
                )
            },
        )

    requested_path = (FRONTEND_DIST / frontend_path).resolve()

    try:
        requested_path.relative_to(FRONTEND_DIST.resolve())
    except ValueError:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    if requested_path.is_file():
        return FileResponse(requested_path)

    return FileResponse(FRONTEND_INDEX)
