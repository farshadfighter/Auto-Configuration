from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.api import api_router
from app.core.config import get_settings
from app.db.session import SessionLocal

settings = get_settings()

if settings.environment != "development" and settings.jwt_secret_key == "change-me-in-production":
    raise RuntimeError(
        "NGFABRIC_JWT_SECRET_KEY is still set to its insecure default. "
        "Set a unique secret before running outside development."
    )

app = FastAPI(title=settings.app_name, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        error_body = detail
    else:
        error_body = {"code": "HTTP_ERROR", "message": str(detail), "details": {}}
    return JSONResponse(status_code=exc.status_code, content={"success": False, "error": error_body})


app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def health_db():
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok"}
    finally:
        db.close()
