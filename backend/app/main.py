from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app import __version__
from app.api.v1.routes import auth, jobs, sessions
from app.core.config import get_settings
from app.core.limiter import limiter
from app.core.logging import configure_logging, get_logger
from app.core.middleware import TraceIdMiddleware, register_error_handlers
from app.ws import routes as ws_routes
from app.ws.session_manager import hub as ws_hub

settings = get_settings()
configure_logging(settings.app_debug)
log = get_logger("app.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("api.startup", env=settings.app_env, version=__version__)
    await ws_hub.start()
    try:
        yield
    finally:
        await ws_hub.stop()
        log.info("api.shutdown")


app = FastAPI(
    title="Protocol AI",
    version=__version__,
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Trace-Id"],
)
app.add_middleware(TraceIdMiddleware)
register_error_handlers(app)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__, "env": settings.app_env}


API_V1 = "/api/v1"
app.include_router(auth.router, prefix=f"{API_V1}/auth", tags=["auth"])
app.include_router(jobs.router, prefix=API_V1, tags=["jobs"])
app.include_router(sessions.router, prefix=f"{API_V1}/sessions", tags=["sessions"])
app.include_router(ws_routes.router, tags=["ws"])
