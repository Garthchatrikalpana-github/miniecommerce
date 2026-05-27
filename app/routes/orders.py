from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cart import Cart
from app.models.order import Order, OrderItem
from app.logging_config import get_logger

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
logger = get_logger("orders")


@router.post("/checkout")
def checkout(request: Request, db: Session = Depends(get_db)):
    # BUG FIX: user_id was hardcoded as 1, total_amount was hardcoded as 499.99
    user_id = request.session.get("user_id")
    if not user_id:
        logger.warning("Unauthenticated checkout attempt")
        return RedirectResponse("/login", status_code=302)

    logger.debug("Checkout initiated: user_id=%d", user_id)

    cart_items = db.query(Cart).filter(Cart.user_id == user_id).all()
    if not cart_items:
        logger.warning("Checkout attempted with empty cart: user_id=%d", user_id)
        return RedirectResponse("/cart", status_code=302)

    # validate stock before committing anything
    for ci in cart_items:
        if ci.product.stock < ci.quantity:
            logger.error(
                "Checkout failed — insufficient stock: product_id=%d available=%d requested=%d",
                ci.product_id, ci.product.stock, ci.quantity,
            )
            return RedirectResponse("/cart", status_code=302)

    total = sum(ci.product.price * ci.quantity for ci in cart_items)
    logger.debug("Checkout total calculated: user_id=%d total=%.2f", user_id, total)

    order = Order(user_id=user_id, total_amount=total, status="placed")
    db.add(order)
    db.flush()   # get order.id before adding items

    for ci in cart_items:
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=ci.product_id,
                quantity=ci.quantity,
                unit_price=ci.product.price,
            )
        )
        # deduct stock
        ci.product.stock -= ci.quantity
        logger.debug(
            "Order item added: order_id=%d product_id=%d qty=%d",
            order.id, ci.product_id, ci.quantity,
        )

    # clear cart
    for ci in cart_items:
        db.delete(ci)

    db.commit()
    logger.info(
        "Order placed successfully: order_id=%d user_id=%d total=%.2f items=%d",
        order.id, user_id, total, len(cart_items),
    )
    return RedirectResponse("/orders", status_code=302)


@router.get("/orders", response_class=HTMLResponse)
def order_history(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        logger.warning("Unauthenticated access to /orders")
        return RedirectResponse("/login", status_code=302)

    logger.debug("Fetching order history: user_id=%d", user_id)
    orders = (
        db.query(Order)
        .filter(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .all()
    )
    logger.info("Orders page loaded: user_id=%d order_count=%d", user_id, len(orders))

    return templates.TemplateResponse(
        "orders.html",
        {
            "request": request,
            "orders": orders,
            "username": request.session.get("username"),
        },
    )
