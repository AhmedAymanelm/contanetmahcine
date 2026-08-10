from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Optional
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.api.deps import get_db
from app.core.security import verify_password, create_access_token
from app.models.user import User
from app.models.oauth_token import OAuthToken
from app.services.social.threads_service import ThreadsService
from app.services.social.linkedin_service import LinkedInService
from app.services.social.snapchat_service import SnapchatService
from app.services.social.tiktok_service import TikTokService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
threads_service = ThreadsService()
linkedin_service = LinkedInService()
tiktok_service = TikTokService()

@router.post("/login")
def login_for_access_token(
    db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=1440)
    access_token = create_access_token(
        subject=str(user.id), expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

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

# --- Snapchat OAuth ---
@router.get("/snapchat")
def auth_snapchat():
    """Redirects the user to Snapchat's OAuth login page."""
    try:
        snapchat_service = SnapchatService()
        auth_url = snapchat_service.get_auth_url()
        return RedirectResponse(auth_url)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})

@router.get("/snapchat/callback")
async def auth_snapchat_callback(
    code: Optional[str] = Query(None, description="Authorization code from Snapchat"),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Handles the OAuth callback from Snapchat."""
    if error:
        logger.error(f"Snapchat OAuth Error: {error} - {error_description}")
        return JSONResponse(status_code=400, content={"status": "error", "message": error_description})

    if not code:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Missing authorization code. Did you visit the callback URL directly?"})

    snapchat_service = SnapchatService()
    exchange_res = await snapchat_service.exchange_code(code)
    if not exchange_res.get("success"):
        return JSONResponse(status_code=400, content={"status": "error", "message": exchange_res.get("message")})
        
    snapchat_service.save_token(db, exchange_res.get("data", {}))
    return RedirectResponse("/?snapchat_connected=true")


# ─── TikTok OAuth 2.0 ─────────────────────────────────────────────────────────

@router.get("/tiktok")
def auth_tiktok():
    """Redirect the user to TikTok's OAuth v2 authorization page."""
    try:
        url, _state = tiktok_service.generate_auth_url()
        return RedirectResponse(url)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})


@router.get("/tiktok/callback")
async def auth_tiktok_callback(
    code: Optional[str] = Query(None, description="Authorization code from TikTok"),
    state: Optional[str] = Query(None, description="State for CSRF protection"),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Handle TikTok OAuth callback: validate state, exchange code, store tokens."""
    # 1. Surface any OAuth-level errors from TikTok
    if error:
        logger.error(f"TikTok OAuth error returned: {error}")
        if error == "access_denied":
            return JSONResponse(status_code=400, content={
                "status": "error", "message": "User denied access to TikTok."
            })
        return JSONResponse(status_code=400, content={
            "status": "error", "message": error_description or error
        })

    # 2. Validate state (CSRF protection)
    if not state or not tiktok_service.validate_state(state):
        logger.warning("TikTok callback received invalid or expired state")
        return JSONResponse(status_code=400, content={
            "status": "error",
            "message": "Invalid or expired state parameter. Please try connecting again."
        })

    # 3. Require authorization code
    if not code:
        return JSONResponse(status_code=400, content={
            "status": "error", "message": "Missing authorization code."
        })

    # 4. Exchange code for tokens (client_secret never logged)
    exchange_res = await tiktok_service.exchange_code(code)
    if not exchange_res.get("success"):
        err = exchange_res.get("error", "unknown")
        detail = exchange_res.get("detail", "")

        if err == "invalid_grant":
            msg = "The authorization code is invalid or has already been used."
        elif err == "invalid_client":
            msg = "TikTok client credentials are misconfigured."
        elif err == "invalid_scope":
            msg = "One or more requested scopes are not approved for this app."
        else:
            msg = f"Failed to exchange authorization code: {err}"

        logger.error(f"TikTok code exchange failed: error={err}")
        return JSONResponse(status_code=400, content={"status": "error", "message": msg})

    # 5. Persist tokens
    token_data = exchange_res["data"]
    tiktok_service.save_token(db, token_data)

    return RedirectResponse("/?tiktok_connected=true")


@router.get("/tiktok/status")
def auth_tiktok_status(db: Session = Depends(get_db)):
    """Return TikTok connection status. Never exposes tokens."""
    return tiktok_service.get_status(db)
