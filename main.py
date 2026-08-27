from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from app.routers import auth, grantee, grantor, admin, superuser, grantor_forms
from app.config import settings
import os

# Create FastAPI app
app = FastAPI(title=settings.APP_NAME)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="app/templates")



# Include routers
app.include_router(auth.router)
app.include_router(grantee.router)
app.include_router(grantor.router)
app.include_router(admin.router)
app.include_router(superuser.router)
app.include_router(grantor_forms.router)

@app.get("/")
async def root():
    """Redirect root to login"""
    return RedirectResponse(url="/login")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

# Custom exception handlers
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Custom 404 page"""
    return templates.TemplateResponse(
        "error.html",
        {"request": request, "error": "Page not found", "code": 404},
        status_code=404
    )

@app.exception_handler(500)
async def server_error_handler(request: Request, exc: Exception):
    """Custom 500 page"""
    return templates.TemplateResponse(
        "error.html",
        {"request": request, "error": "Internal server error", "code": 500},
        status_code=500
    )