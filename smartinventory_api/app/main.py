from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from app.api.v1 import items, auth, health, orders
from app.models.database import init_db
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger("main")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Code before `yield` runs on startup, code after runs on shutdown.
    We use this to set up the database when the server starts.
    """
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    await init_db()
    logger.info("Database ready")
    yield
    logger.info("Server shutting down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
A REST API for managing product inventory.

**Features:**
- JWT-based authentication
- Full CRUD for inventory items
- Pagination and filtering
- Stock quantity management
- Soft deletes (data is never permanently lost)

**Getting started:**
1. Log in via `POST /api/v1/auth/token` to get a JWT token
2. Click **Authorize** and paste the token
3. Explore the inventory endpoints
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ── Middleware ────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Restrict to specific domains in production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


# ── Routers ───────────────────────────────────────────────────────

app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(items.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")


# ── Error Handlers ────────────────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """
    Convert Pydantic validation errors into a readable format.
    FastAPI's default format is verbose; this makes it cleaner for API consumers.
    """
    errors = []
    for err in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in err["loc"] if loc != "body"),
            "message": err["msg"],
        })
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation failed", "errors": errors},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch-all error handler — prevents raw stack traces from leaking to clients.
    The full error is logged server-side for debugging.
    """
    logger.error(f"Unhandled error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred."},
    )
