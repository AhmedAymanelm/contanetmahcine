from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pathlib import Path

class Settings(BaseSettings):
    PROJECT_NAME: str = "Content Machine API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    # Environment
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    
    # Scraper Settings
    REQUEST_TIMEOUT: int = 30
    
    # Database
    DATABASE_URL: str
    
    # AI 
    ANTHROPIC_API_KEY: str = ""
    
    # Social Media integration
    INSTAGRAM_ACCESS_TOKEN: Optional[str] = None
    INSTAGRAM_ACCOUNT_ID: Optional[str] = None
    FACEBOOK_ACCESS_TOKEN: Optional[str] = None
    FACEBOOK_PAGE_ID: Optional[str] = None
    PUBLIC_SERVER_URL: Optional[str] = None
    
    # Threads OAuth
    THREADS_CLIENT_ID: Optional[str] = None
    THREADS_CLIENT_SECRET: Optional[str] = None
    THREADS_REDIRECT_URI: str = "https://contanetmahcine.up.railway.app/auth/threads/callback"
    
    # LinkedIn OAuth
    LINKEDIN_CLIENT_ID: Optional[str] = None
    LINKEDIN_CLIENT_SECRET: Optional[str] = None
    LINKEDIN_REDIRECT_URI: str = "https://contanetmahcine.up.railway.app/auth/linkedin/callback"
    
    model_config = SettingsConfigDict(env_file=str(Path(__file__).resolve().parent.parent.parent / ".env"), env_file_encoding="utf-8", extra="ignore")

settings = Settings()
