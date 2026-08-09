from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.api.deps import get_db
from app.models.oauth_token import OAuthToken
from app.services.social.threads_service import ThreadsService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
threads_service = ThreadsService()

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
    code: str = Query(..., description="Authorization code from Threads"),
    error: str = Query(None),
    error_reason: str = Query(None),
    error_description: str = Query(None),
    db: Session = Depends(get_db)
):
    """Handles the OAuth callback from Threads."""
    if error:
        logger.error(f"Threads OAuth Error: {error} - {error_reason} - {error_description}")
        return JSONResponse(status_code=400, content={"status": "error", "message": error_description})

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
    
    return RedirectResponse("http://localhost:8000/?threads_connected=true")
