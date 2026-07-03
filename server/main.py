import os

import psycopg2
from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

app = FastAPI(title="mc_wallet")

DATABASE_URL = os.getenv("DATABASE_URL")


@app.get("/health")
def health():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.close()
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        return {"status": "error", "db": str(e)}
