from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import logging
import sys
from datetime import datetime

from app.core.config import settings
from app.core.database import init_db
from app.routers import auth, preorder, orders, webhooks, dashboard

# Configure logging
handlers = [logging.StreamHandler(sys.stdout)]
if settings.LOG_FILE:
    import os
    os.makedirs(os.path.dirname(settings.LOG_FILE), exist_ok=True)
    handlers.append(logging.FileHandler(settings.LOG_FILE))

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=handlers
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for the application"""
    logger.info("Starting School Payment System...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
    yield
    logger.info("Shutting down School Payment System...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="School Invoice Payment System for Scolapp.com - Integrated with D-Money Gateway",
    lifespan=lifespan,
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
    openapi_url=f"{settings.API_PREFIX}/openapi.json"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests"""
    start_time = datetime.utcnow()
    response = await call_next(request)
    duration = (datetime.utcnow() - start_time).total_seconds()
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - Duration: {duration:.3f}s"
    )
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"success": False, "error": "Validation error", "detail": exc.errors()}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An error occurred"
        }
    )


# Include routers
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(preorder.router, prefix=settings.API_PREFIX)
app.include_router(orders.router, prefix=settings.API_PREFIX)
app.include_router(webhooks.router, prefix=settings.API_PREFIX)
app.include_router(dashboard.router, prefix=settings.API_PREFIX)


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "online",
        "docs": f"{settings.API_PREFIX}/docs",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.ENVIRONMENT
    }


@app.get(f"{settings.API_PREFIX}/info")
async def api_info():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "School Invoice Payment System",
        "endpoints": {
            "authentication": f"{settings.API_PREFIX}/auth/token",
            "preorder": f"{settings.API_PREFIX}/preorder",
            "query_order": f"{settings.API_PREFIX}/orders/{{order_id}}",
            "webhook": f"{settings.API_PREFIX}/webhooks/dmoney",
            "dashboard": {
                "stats": f"{settings.API_PREFIX}/dashboard/stats",
                "transactions": f"{settings.API_PREFIX}/dashboard/transactions",
                "revenue": f"{settings.API_PREFIX}/dashboard/revenue",
                "guardian_history": f"{settings.API_PREFIX}/dashboard/guardian/{{phone}}/history"
            }
        },
        "documentation": f"{settings.API_PREFIX}/docs",
        "payment_gateway": "D-Money",
        "currency": settings.PAYMENT_CURRENCY
    }
