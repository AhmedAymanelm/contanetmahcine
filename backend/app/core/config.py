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
    # Security (JWT Auth)
    SECRET_KEY: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7" # Default secret for dev
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440 # 24 hours
    
    # AI 
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_PAUSED: bool = False
    
    # Social Media integration
    INSTAGRAM_ACCESS_TOKEN: Optional[str] = None
    INSTAGRAM_ACCOUNT_ID: Optional[str] = None
    INSTAGRAM_PAUSED: bool = False
    FACEBOOK_ACCESS_TOKEN: Optional[str] = None
    FACEBOOK_PAGE_ID: Optional[str] = None
    FACEBOOK_PAUSED: bool = False
    PUBLIC_SERVER_URL: Optional[str] = None
    
    # Threads OAuth
    THREADS_CLIENT_ID: Optional[str] = None
    THREADS_CLIENT_SECRET: Optional[str] = None
    THREADS_REDIRECT_URI: str = "https://contanetmahcine.up.railway.app/auth/threads/callback"
    THREADS_PAUSED: bool = False
    
    # LinkedIn OAuth
    LINKEDIN_CLIENT_ID: Optional[str] = None
    LINKEDIN_CLIENT_SECRET: Optional[str] = None
    LINKEDIN_REDIRECT_URI: str = "https://contanetmahcine.up.railway.app/auth/linkedin/callback"
    LINKEDIN_PAUSED: bool = False
    
    # Snapchat OAuth
    SNAPCHAT_CLIENT_ID: Optional[str] = None
    SNAPCHAT_CLIENT_SECRET: Optional[str] = None
    SNAPCHAT_REDIRECT_URI: str = "https://contanetmahcine.up.railway.app/auth/snapchat/callback"
    SNAPCHAT_PAUSED: bool = False
    
    # Twitter (X) Auth
    TWITTER_API_KEY: Optional[str] = None
    TWITTER_API_SECRET: Optional[str] = None
    TWITTER_ACCESS_TOKEN: Optional[str] = None
    TWITTER_ACCESS_SECRET: Optional[str] = None
    TWITTER_PAUSED: bool = False

    # TikTok OAuth
    TIKTOK_CLIENT_KEY: Optional[str] = None
    TIKTOK_CLIENT_SECRET: Optional[str] = None
    TIKTOK_REDIRECT_URI: str = "https://contanetmahcine.up.railway.app/auth/tiktok/callback"
    TIKTOK_PAUSED: bool = False
    
    model_config = SettingsConfigDict(env_file=str(Path(__file__).resolve().parent.parent.parent / ".env"), env_file_encoding="utf-8", extra="ignore")

settings = Settings()
