from pathlib import Path

import psycopg2
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routers.auth import router as auth_router
from app.api.routers.users import router as users_router
from app.config import settings

Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)

app = FastAPI(title="mc_wallet")

app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(users_router, prefix="/users", tags=["users"])


@app.get("/health")
def health():
    try:
        conn = psycopg2.connect(settings.database_url)
        conn.close()
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        return {"status": "error", "db": str(e)}
