"""
Entry point for the School Payment System.

Run with:
    uvicorn main:app          (development, from project root)
    uvicorn app.main:app      (production / systemd)
    python main.py            (development with auto-reload)
"""
from app.main import app  # noqa: F401 - re-export app for uvicorn

if __name__ == "__main__":
    import uvicorn
    from app.core.config import settings
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
