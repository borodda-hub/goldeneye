from fastapi import FastAPI

app = FastAPI(title="NGTI API", version="0.1.0")


@app.get("/v1/health")
async def health() -> dict[str, bool]:
    return {"ok": True}
