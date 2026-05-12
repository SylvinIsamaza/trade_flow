from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routers import (
    auth, users, accounts, trades, analytics, reports,
    comments, tags, strategies, notes, insights,
    notifications, sessions, import_trades
)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(accounts.router, prefix="/api")
app.include_router(trades.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(comments.router, prefix="/api")
app.include_router(tags.router, prefix="/api")
app.include_router(strategies.router, prefix="/api")
app.include_router(notes.router, prefix="/api")
app.include_router(insights.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(import_trades.router, prefix="/api")
app.include_router(reports.router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Welcome to Tradeflow API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}