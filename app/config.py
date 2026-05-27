# BUG FIX: pydantic v2 moved BaseSettings to pydantic-settings package
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    SESSION_SECRET: str = "change-this-in-production"

    class Config:
        env_file = ".env"


settings = Settings()
