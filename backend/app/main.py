from fastapi import FastAPI
from app.api.dashboard import router as dashboard_router

app = FastAPI()

app.include_router(
    dashboard_router,
    prefix="/api/dashboard",
    tags=["Dashboard"]
)