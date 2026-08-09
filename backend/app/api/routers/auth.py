from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.api.deps import get_db
from app.models.oauth_token import OAuthToken
from app.services.social.threads_service import ThreadsService
from app.services.social.linkedin_service import LinkedInService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
threads_service = ThreadsService()
linkedin_service = LinkedInService()

@router.get("/threads")
def auth_threads():
    """Redirects the user to the Threads OAuth authorization page."""
    try:
        auth_url = threads_service.generate_auth_url()
        return RedirectResponse(auth_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/threads/callback")
async def auth_threads_callback(
    code: Optional[str] = Query(None, description="Authorization code from Threads"),
    error: Optional[str] = Query(None),
    error_reason: str = Query(None),
    error_description: str = Query(None),
    db: Session = Depends(get_db)
):
    """Handles the OAuth callback from Threads."""
    if error:
        logger.error(f"Threads OAuth Error: {error} - {error_reason} - {error_description}")
        return JSONResponse(status_code=400, content={"status": "error", "message": error_description})

    if not code:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Missing authorization code."})

    # 1. Exchange code for short-lived token
    exchange_res = await threads_service.exchange_code(code)
    if not exchange_res.get("success"):
        return JSONResponse(status_code=400, content={"status": "error", "message": "Failed to exchange code."})
    
    short_token = exchange_res["data"]["access_token"]
    
    # 2. Exchange for long-lived token
    long_res = await threads_service.get_long_lived_token(short_token)
    if not long_res.get("success"):
        return JSONResponse(status_code=400, content={"status": "error", "message": "Failed to get long-lived token."})
    
    long_token = long_res["data"]["access_token"]
    expires_in = long_res["data"].get("expires_in", 5184000) # Default 60 days
    
    # 3. Fetch basic user profile
    profile_res = await threads_service.get_user_profile(long_token)
    if not profile_res.get("success"):
        return JSONResponse(status_code=400, content={"status": "error", "message": "Failed to fetch user profile."})
    
    account_id = profile_res["data"].get("id")
    
    # 4. Save to DB
    token_entry = db.query(OAuthToken).filter(OAuthToken.platform == "threads").first()
    if not token_entry:
        token_entry = OAuthToken(platform="threads")
        db.add(token_entry)
        
    token_entry.access_token = long_token
    token_entry.account_id = account_id
    token_entry.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    
    db.commit()
    
    return RedirectResponse("/?threads_connected=true")

@router.get("/linkedin")
def auth_linkedin():
    """Redirects the user to the LinkedIn OAuth authorization page."""
    try:
        auth_url = linkedin_service.generate_auth_url()
        return RedirectResponse(auth_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/linkedin/callback")
async def auth_linkedin_callback(
    code: Optional[str] = Query(None, description="Authorization code from LinkedIn"),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Handles the OAuth callback from LinkedIn."""
    if error:
        logger.error(f"LinkedIn OAuth Error: {error} - {error_description}")
        return JSONResponse(status_code=400, content={"status": "error", "message": error_description})

    if not code:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Missing authorization code. Did you visit the callback URL directly?"})

    # 1. Exchange code for token
    exchange_res = await linkedin_service.exchange_code(code)
    if not exchange_res.get("success"):
        return JSONResponse(status_code=400, content={"status": "error", "message": "Failed to exchange code."})
    
    access_token = exchange_res["data"]["access_token"]
    expires_in = exchange_res["data"].get("expires_in", 5184000) # Default 60 days
    
    # 2. Fetch basic user profile to get URN
    profile_res = await linkedin_service.get_user_profile(access_token)
    if not profile_res.get("success"):
        return JSONResponse(status_code=400, content={"status": "error", "message": "Failed to fetch user profile."})
    
    account_id = profile_res["data"].get("sub") # The Person ID URN base
    if not account_id:
        return JSONResponse(status_code=400, content={"status": "error", "message": "No sub returned from userinfo."})
    
    # 3. Save to DB
    token_entry = db.query(OAuthToken).filter(OAuthToken.platform == "linkedin").first()
    if not token_entry:
        token_entry = OAuthToken(platform="linkedin")
        db.add(token_entry)
        
    token_entry.access_token = access_token
    token_entry.account_id = account_id
    token_entry.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    
    db.commit()
    
    return RedirectResponse("/?linkedin_connected=true")
