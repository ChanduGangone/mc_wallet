from fastapi import FastAPI

app = FastAPI(title="mc_wallet")


@app.get("/health")
def health():
    return {"status": "ok"}
