import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.logging_config import get_logger

router = APIRouter(prefix="/simulate", tags=["simulator"])
logger = get_logger("simulator")


@router.get("/db-failure")
def db_failure():
    """
    BUG FIX: original raised a bare Exception which produces an unhandled 500
    with no useful body. Now returns a structured JSON error with proper logging.
    """
    logger.error("SIMULATED | Database connection failure triggered")
    return JSONResponse(
        status_code=503,
        content={"error": "database_unavailable", "message": "Simulated DB outage"},
    )


@router.get("/timeout")
def timeout():
    logger.warning("SIMULATED | API timeout triggered — sleeping 15s")
    time.sleep(15)
    logger.debug("SIMULATED | Timeout endpoint completed after sleep")
    return {"message": "Completed after delay"}


@router.get("/payment-failure")
def payment_failure():
    logger.error("SIMULATED | Payment gateway timeout — transaction declined")
    return JSONResponse(
        status_code=402,
        content={"status": "payment_failed", "reason": "gateway_timeout"},
    )


@router.get("/out-of-stock")
def out_of_stock():
    logger.warning("SIMULATED | Product out-of-stock scenario triggered")
    return JSONResponse(
        status_code=409,
        content={"error": "out_of_stock", "product_id": 42},
    )


@router.get("/auth-failure")
def auth_failure():
    logger.warning("SIMULATED | Authentication failure — invalid token")
    return JSONResponse(
        status_code=401,
        content={"error": "unauthorized", "message": "Token expired or invalid"},
    )
