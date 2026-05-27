from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.product import Product
from app.logging_config import get_logger

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
logger = get_logger("products")


@router.get("/products", response_class=HTMLResponse)
def products(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        logger.warning("Unauthenticated access to /products — redirecting to login")
        return RedirectResponse("/login", status_code=302)

    logger.debug("Fetching product list for user_id=%s", user_id)
    product_list = db.query("Product").all()
    logger.info("Products page loaded: count=%d user_id=%s", len(product_list), user_id)

    return templates.TemplateResponse(
        "products.html",
        {
            "request": request,
            "products": product_list,
            "username": request.session.get("username"),
        },
    )
