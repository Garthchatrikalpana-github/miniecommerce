import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
# from fastapi.templating import Jinja2Templates

from app.config import settings
from app.database import Base, engine
from app.routes import auth, products, cart, orders, simulator
from app.logging_config import logger

# import all models so metadata is populated before create_all
import app.models.user    # noqa
import app.models.product # noqa
import app.models.cart    # noqa
import app.models.order   # noqa

# create tables
Base.metadata.create_all(bind=engine)
logger.info("Database tables verified / created")

app = FastAPI(title="Mini Commerce", version="1.0.0")

# BUG FIX: SessionMiddleware was missing — session reads/writes silently failed
app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
# templates = Jinja2Templates(directory="app/templates")

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(simulator.router)

# print(type(templates))


# ── global exception handler ───────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception: path=%s method=%s error=%s",
        request.url.path, request.method, str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "detail": str(exc)},
    )


@app.on_event("startup")
async def startup():
    logger.info("Mini Commerce application started — version=1.0.0")


@app.on_event("shutdown")
async def shutdown():
    logger.info("Mini Commerce application shutting down")
