from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any
from app.services.social.instagram import InstagramService
from app.services.social.facebook import FacebookService

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
