from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.database import get_db
from app.models.user import User
from app.logging_config import get_logger

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
# templates.env.cache = {}  
logger = get_logger("auth")

# BUG FIX: CryptContext was never used — passwords were stored/checked in plaintext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)
# def hash_password(password: str):
#     password = password[:72]  # safe guard for bcrypt
#     return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    logger.debug("POST /login attempt for user=%s", username)

    # BUG FIX: original code only checked username existence, never verified password
    user = db.query(User).filter(User.username == username).first()

    if not user:
        logger.warning("Login failed — user not found: username=%s", username)
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid username or password"},
            status_code=401,
        )

    if not verify_password(password, user.hashed_password):
        logger.warning("Login failed — wrong password: username=%s", username)
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid username or password"},
            status_code=401,
        )

    logger.info("Login successful: username=%s user_id=%d", username, user.id)

    # BUG FIX: store user_id in session instead of hardcoding 1 everywhere
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    return RedirectResponse("/products", status_code=302)


@router.get("/logout")
def logout(request: Request):
    username = request.session.get("username", "unknown")
    request.session.clear()
    logger.info("User logged out: username=%s", username)
    return RedirectResponse("/login", status_code=302)


@router.post("/register")
def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    logger.debug("POST /register attempt: username=%s", username)

    existing = db.query(User).filter(User.username == username).first()
    if existing:
        logger.warning("Registration failed — username taken: %s", username)
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Username already taken"},
            status_code=409,
        )

    user = User(username=username, hashed_password=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info("New user registered: username=%s user_id=%d", username, user.id)
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    return RedirectResponse("/products", status_code=302)
