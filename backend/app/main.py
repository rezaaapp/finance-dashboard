from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from gspread.exceptions import APIError

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.config import settings
from app.database import close_database_pool

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
    return {
        "service": "finance-dashboard-api",
        "status": "ok",
        "health": "/api/health",
    }


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


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

app.include_router(admin_router)
