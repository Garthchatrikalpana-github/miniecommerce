from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cart import Cart
from app.models.product import Product
from app.logging_config import get_logger

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
logger = get_logger("cart")


@router.post("/cart/add/{product_id}")
def add_to_cart(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    # BUG FIX: user_id was hardcoded as 1
    user_id = request.session.get("user_id")
    if not user_id:
        logger.warning("Unauthenticated cart add attempt for product_id=%d", product_id)
        return RedirectResponse("/login", status_code=302)

    logger.debug("Adding to cart: user_id=%d product_id=%d", user_id, product_id)

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        logger.error("Cart add failed — product not found: product_id=%d", product_id)
        return RedirectResponse("/products", status_code=302)

    if product.stock < 1:
        logger.warning(
            "Cart add failed — out of stock: product_id=%d name=%s", product_id, product.name
        )
        return RedirectResponse("/products", status_code=302)

    # if item already exists, increment quantity
    existing = (
        db.query(Cart)
        .filter(Cart.user_id == user_id, Cart.product_id == product_id)
        .first()
    )
    if existing:
        existing.quantity += 1
        logger.debug(
            "Incremented cart item: user_id=%d product_id=%d new_qty=%d",
            user_id, product_id, existing.quantity,
        )
    else:
        item = Cart(user_id=user_id, product_id=product_id, quantity=1)
        db.add(item)
        logger.debug("New cart item added: user_id=%d product_id=%d", user_id, product_id)

    db.commit()
    logger.info(
        "Cart updated: user_id=%d product_id=%d product_name=%s", user_id, product_id, product.name
    )
    return RedirectResponse("/cart", status_code=302)


@router.get("/cart", response_class=HTMLResponse)
def view_cart(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        logger.warning("Unauthenticated access to /cart")
        return RedirectResponse("/login", status_code=302)

    logger.debug("Loading cart for user_id=%d", user_id)
    items = (
        db.query(Cart)
        .filter(Cart.user_id == user_id)
        .all()
    )
    total = sum(i.product.price * i.quantity for i in items)
    logger.info("Cart viewed: user_id=%d items=%d total=%.2f", user_id, len(items), total)

    return templates.TemplateResponse(
        "cart.html",
        {
            "request": request,
            "items": items,
            "total": total,
            "username": request.session.get("username"),
        },
    )


@router.post("/cart/remove/{item_id}")
def remove_from_cart(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/login", status_code=302)

    item = db.query(Cart).filter(Cart.id == item_id, Cart.user_id == user_id).first()
    if not item:
        logger.warning(
            "Cart remove failed — item not found or not owned: item_id=%d user_id=%d",
            item_id, user_id,
        )
        return RedirectResponse("/cart", status_code=302)

    logger.info("Cart item removed: item_id=%d user_id=%d product_id=%d", item_id, user_id, item.product_id)
    db.delete(item)
    db.commit()
    return RedirectResponse("/cart", status_code=302)
