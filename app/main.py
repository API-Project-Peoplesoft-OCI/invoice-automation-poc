from app.config import settings
from app.models import Invoice
from app.routes.invoices import router as invoices_router
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title=settings.app_name,
    description="Invoice extraction and validation using OCI Document Understanding",
    version="0.1.0",
)

app.include_router(invoices_router)

app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static",
)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/")
async def upload_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="upload.html",
        context={
            "page_title": "Invoice Extraction POC",
        },
    )


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "application": settings.app_name,
        "environment": settings.environment,
        "input_bucket": settings.input_bucket,
        "output_bucket": settings.output_bucket,
    }
@app.post("/api/invoices/validate")
async def validate_invoice(invoice: Invoice):
    return {
        "status": "valid",
        "invoice": invoice.model_dump(mode="json"),
    }