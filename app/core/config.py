# app/core/config.py
import os
from pydantic_settings import BaseSettings # Correct for Pydantic v2 based settings
from dotenv import load_dotenv
from typing import List, Optional

load_dotenv() # Needs to be effective BEFORE Settings class is instantiated if .env is primary source

class Settings(BaseSettings):
    PROJECT_NAME: str = "Communify Backend"
    API_V1_STR: str = "/api/v1"

    DATABASE_URL: str = os.getenv("DATABASE_URL", "mongodb://localhost:27017")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "communify_db")

    # JWT settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "a_very_weak_default_key_min_32_chars_is_better") # Default for illustration
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost", "http://localhost:8081"]
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

    # For pydantic-settings, you configure .env loading via model_config
    # class Config: # This is Pydantic V1 style
    #     case_sensitive = True
    #     env_file = ".env" 
    #     env_file_encoding = "utf-8"

    # Pydantic V2 style for pydantic-settings
    # model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra='ignore', case_sensitive=True)
    # If not using model_config for env_file, load_dotenv() is crucial and must be effective.

settings = Settings() # Instantiation happens here

# This print statement is good for debugging
print(f"--- CONFIG LOADED --- SECRET_KEY: '{settings.SECRET_KEY}' (Type: {type(settings.SECRET_KEY)}) ---")
print(f"--- CONFIG LOADED --- ALGORITHM: '{settings.ALGORITHM}' ---")
print(f"--- CONFIG LOADED --- ACCESS_TOKEN_EXPIRE_MINUTES: {settings.ACCESS_TOKEN_EXPIRE_MINUTES} ---")


if settings.LOG_LEVEL not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
    print(f"WARNING: Invalid LOG_LEVEL '{settings.LOG_LEVEL}'. Defaulting to INFO.")
    settings.LOG_LEVEL = "INFO"