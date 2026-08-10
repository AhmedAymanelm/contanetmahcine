from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any
from app.services.social.instagram import InstagramService
from app.services.social.facebook import FacebookService
from app.services.social.linkedin_service import LinkedInService
from app.services.social.threads_service import ThreadsService
from app.services.social.snapchat_service import SnapchatService
from app.api.deps import get_db
from sqlalchemy.orm import Session

router = APIRouter()

class InstagramPublishRequest(BaseModel):
    image_url: str
    caption: str

def get_instagram_service():
    return InstagramService()

@router.get("/facebook/status")
async def get_facebook_status():
    """Check Facebook Pages API connection status"""
    try:
        service = FacebookService()
        return await service.check_status()
    except Exception as e:
        return {"connected": False, "error": str(e)}

@router.get("/linkedin/status")
async def get_linkedin_status(db: Session = Depends(get_db)):
    """Check LinkedIn connection status"""
    try:
        service = LinkedInService()
        return service.get_status(db)
    except Exception as e:
        return {"connected": False, "error": str(e)}

@router.get("/instagram/status")
async def get_instagram_status(service: InstagramService = Depends(get_instagram_service)):
    """
    Check the connectivity status of the configured Instagram account.
    """
    return await service.check_status()

@router.post("/instagram/publish")
async def publish_to_instagram(
    request: InstagramPublishRequest,
    service: InstagramService = Depends(get_instagram_service)
):
    """
    Publish an image with a caption to the configured Instagram account.
    Note: The image_url must be publicly accessible by Meta's servers.
    """
    result = await service.publish_image(
        image_url=request.image_url,
        caption=request.caption
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result
        )
        
    return result

@router.get("/snapchat/status")
async def get_snapchat_status(db: Session = Depends(get_db)):
    """Check Snapchat connection status"""
    try:
        service = SnapchatService()
        return service.get_status(db)
    except Exception as e:
        return {"connected": False, "error": str(e)}


# ─── TikTok ───────────────────────────────────────────────────────────────────

from app.services.social.tiktok_service import TikTokService
from typing import Optional

class TikTokPublishRequest(BaseModel):
    video_url: str
    title: str = ""
    privacy_level: str = "SELF_ONLY"
    disable_comment: bool = False
    disable_duet: bool = False
    disable_stitch: bool = False

@router.get("/tiktok/status")
def get_tiktok_status(db: Session = Depends(get_db)):
    """Check TikTok OAuth connection status (no tokens exposed)."""
    try:
        service = TikTokService()
        return service.get_status(db)
    except Exception as e:
        return {"connected": False, "error": str(e)}

@router.post("/tiktok/creator-info")
async def tiktok_creator_info(db: Session = Depends(get_db)):
    """
    Query TikTok creator info: privacy level options, max video duration, etc.
    Requires TikTok account to be connected.
    """
    service = TikTokService()
    access_token = await service.get_valid_access_token(db)
    if not access_token:
        raise HTTPException(
            status_code=401,
            detail="TikTok account not connected or token expired. Visit /auth/tiktok to connect."
        )
    result = await service.get_creator_info(access_token)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("detail", result.get("error")))
    return result["data"]

@router.post("/tiktok/publish")
async def tiktok_publish_video(
    request: TikTokPublishRequest,
    db: Session = Depends(get_db)
):
    """
    Publish a video to TikTok via PULL_FROM_URL.

    IMPORTANT: Requires `video.publish` scope AND Content Posting API approval
    from TikTok (app review). If not approved, returns a 403 with instructions.
    The video_url must be publicly accessible.
    """
    service = TikTokService()
    access_token = await service.get_valid_access_token(db)
    if not access_token:
        raise HTTPException(
            status_code=401,
            detail="TikTok account not connected or token expired. Visit /auth/tiktok to connect."
        )

    result = await service.publish_video(
        access_token=access_token,
        video_url=request.video_url,
        title=request.title,
        privacy_level=request.privacy_level,
        disable_comment=request.disable_comment,
        disable_duet=request.disable_duet,
        disable_stitch=request.disable_stitch,
    )

    if not result.get("success"):
        err = result.get("error", "")
        if err in ("permission_denied", "scope_not_authorized"):
            raise HTTPException(status_code=403, detail=result.get("detail"))
        raise HTTPException(status_code=400, detail=result.get("detail", err))

    return result["data"]
