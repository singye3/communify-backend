# app/core/config.py
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from typing import List, Optional

# Load .env file at the start
load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "Communify Backend"
    API_V1_STR: str = "/api/v1"

    # Database settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "mongodb://localhost:27017")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "communify_db")

    # JWT settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "default_secret_key_change_this") # Provide a default only for running without .env, CHANGE IT
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    # CORS settings (optional, adjust as needed for your frontend)
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost", "http://localhost:8081"] # Example origins

    class Config:
        case_sensitive = True
        # If using Pydantic V1, use env_file = ".env" instead of load_dotenv()
        # env_file = ".env"


settings = Settings()