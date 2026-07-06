from contextlib import asynccontextmanager
from pathlib import Path

import psycopg2
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routers.auth import router as auth_router
from app.api.routers.exchange_rates import router as exchange_rates_router
from app.api.routers.users import router as users_router
from app.api.routers.wallets import router as wallets_router
from app.config import settings
from app.core.exchange_rates import ensure_todays_snapshot
from app.core.scheduler import shutdown_scheduler, start_scheduler

Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_todays_snapshot()
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title="mc_wallet", lifespan=lifespan)

app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(wallets_router, prefix="/wallets", tags=["wallets"])
app.include_router(exchange_rates_router, prefix="/exchange-rates", tags=["exchange-rates"])


@app.get("/health")
def health():
    try:
        conn = psycopg2.connect(settings.database_url)
        conn.close()
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        return {"status": "error", "db": str(e)}
