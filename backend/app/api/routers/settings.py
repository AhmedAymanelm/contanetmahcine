from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
import dotenv
from pathlib import Path
from pydantic import BaseModel
from typing import Dict, Any, Optional

from app.api.deps import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.oauth_token import OAuthToken

router = APIRouter()

# Locate the .env file
ENV_PATH = Path(settings.model_config.get("env_file", ".env"))

def _update_env(key: str, value: str):
    """Updates the .env file and the in-memory settings."""
    # Update .env
    dotenv.set_key(str(ENV_PATH), key, value)
    
    # Also update settings in memory
    if hasattr(settings, key):
        # Convert bool back if it's a boolean field in config
        if value.lower() == "true":
            setattr(settings, key, True)
        elif value.lower() == "false":
            setattr(settings, key, False)
        else:
            setattr(settings, key, value)


@router.get("/platforms")
async def get_platforms(db: Session = Depends(get_db)):
    """
    Returns the status and configured keys for all platforms.
    Sensitive keys are partially masked.
    """
    def mask(s):
        if not s: return None
        if len(s) <= 8: return "*" * len(s)
        return s[:4] + "*" * (len(s)-8) + s[-4:]

    # Anthropic
    anthropic = {
        "connected": bool(settings.ANTHROPIC_API_KEY),
        "paused": settings.ANTHROPIC_PAUSED,
        "keys": {"ANTHROPIC_API_KEY": mask(settings.ANTHROPIC_API_KEY)}
    }
    
    # Facebook / Instagram (via env)
    facebook = {
        "connected": bool(settings.FACEBOOK_ACCESS_TOKEN and settings.FACEBOOK_PAGE_ID),
        "paused": settings.FACEBOOK_PAUSED,
        "keys": {
            "FACEBOOK_ACCESS_TOKEN": mask(settings.FACEBOOK_ACCESS_TOKEN),
            "FACEBOOK_PAGE_ID": settings.FACEBOOK_PAGE_ID
        }
    }
    instagram = {
        "connected": bool(settings.INSTAGRAM_ACCESS_TOKEN and settings.INSTAGRAM_ACCOUNT_ID),
        "paused": settings.INSTAGRAM_PAUSED,
        "keys": {
            "INSTAGRAM_ACCESS_TOKEN": mask(settings.INSTAGRAM_ACCESS_TOKEN),
            "INSTAGRAM_ACCOUNT_ID": settings.INSTAGRAM_ACCOUNT_ID
        }
    }
    
    # Twitter (X)
    twitter = {
        "connected": bool(settings.TWITTER_API_KEY and settings.TWITTER_ACCESS_TOKEN),
        "paused": settings.TWITTER_PAUSED,
        "keys": {
            "TWITTER_API_KEY": mask(settings.TWITTER_API_KEY),
            "TWITTER_API_SECRET": mask(settings.TWITTER_API_SECRET),
            "TWITTER_ACCESS_TOKEN": mask(settings.TWITTER_ACCESS_TOKEN),
            "TWITTER_ACCESS_SECRET": mask(settings.TWITTER_ACCESS_SECRET),
        }
    }
    
    # OAuth platforms (LinkedIn, Threads, TikTok, Snapchat)
    # We check if there's an OAuthToken in DB for them
    def get_oauth_status(platform_name: str, paused_flag: bool):
        token = db.query(OAuthToken).filter(OAuthToken.platform == platform_name).first()
        client_id_key = f"{platform_name.upper()}_CLIENT_ID"
        client_secret_key = f"{platform_name.upper()}_CLIENT_SECRET"
        # Tiktok has special names in env
        if platform_name == "tiktok":
            client_id_key = "TIKTOK_CLIENT_KEY"
            
        client_id = getattr(settings, client_id_key, None)
        client_secret = getattr(settings, client_secret_key, None)
        
        return {
            "connected": bool(token or (client_id and client_secret)),
            "paused": paused_flag,
            "has_token": bool(token), # if the user authenticated
            "keys": {
                client_id_key: mask(client_id),
                client_secret_key: mask(client_secret)
            }
        }

    return {
        "ai": {
            "anthropic": anthropic
        },
        "social": {
            "facebook": facebook,
            "instagram": instagram,
            "twitter": twitter,
            "linkedin": get_oauth_status("linkedin", settings.LINKEDIN_PAUSED),
            "threads": get_oauth_status("threads", settings.THREADS_PAUSED),
            "tiktok": get_oauth_status("tiktok", settings.TIKTOK_PAUSED),
            "snapchat": get_oauth_status("snapchat", settings.SNAPCHAT_PAUSED),
        }
    }

@router.post("/platforms/{platform}")
async def save_platform_keys(platform: str, keys: Dict[str, str], db: Session = Depends(get_db)):
    """Save or update API keys in .env"""
    for key, value in keys.items():
        # Only update if a value is provided and not masked
        if value and not value.startswith("*") and not value.endswith("*"):
            _update_env(key, value)
    return {"message": "Keys updated successfully"}

@router.delete("/platforms/{platform}")
async def delete_platform_keys(platform: str, db: Session = Depends(get_db)):
    """Remove API keys and any associated OAuth token."""
    # Define keys to clear based on platform
    keys_map = {
        "anthropic": ["ANTHROPIC_API_KEY"],
        "facebook": ["FACEBOOK_ACCESS_TOKEN", "FACEBOOK_PAGE_ID"],
        "instagram": ["INSTAGRAM_ACCESS_TOKEN", "INSTAGRAM_ACCOUNT_ID"],
        "twitter": ["TWITTER_API_KEY", "TWITTER_API_SECRET", "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_SECRET"],
        "linkedin": ["LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET"],
        "threads": ["THREADS_CLIENT_ID", "THREADS_CLIENT_SECRET"],
        "tiktok": ["TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET"],
        "snapchat": ["SNAPCHAT_CLIENT_ID", "SNAPCHAT_CLIENT_SECRET"],
    }
    
    if platform in keys_map:
        for key in keys_map[platform]:
            _update_env(key, "")
            
    # Also delete oauth token if exists
    token = db.query(OAuthToken).filter(OAuthToken.platform == platform).first()
    if token:
        db.delete(token)
        db.commit()

    return {"message": f"{platform} disconnected successfully"}


@router.post("/platforms/{platform}/toggle")
async def toggle_platform(platform: str, body: Dict[str, bool], db: Session = Depends(get_db)):
    """Toggle the pause state of a platform."""
    paused = body.get("paused", False)
    key = f"{platform.upper()}_PAUSED"
    
    _update_env(key, "true" if paused else "false")
    return {"message": f"{platform} pause state updated"}
