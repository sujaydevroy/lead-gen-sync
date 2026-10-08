from fastapi import APIRouter

from app.api.v1 import admin, auth, communications, companies, dashboard, dealers, lookups, sales, users

api_router = APIRouter(prefix="/api/v1")
for module in (auth, users, dealers, lookups, companies, communications, dashboard, sales, admin):
    api_router.include_router(module.router)
