from fastapi import FastAPI

from src.app.lifespan import app_lifespan

app = FastAPI(lifespan=app_lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
