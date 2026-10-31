from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import httpx
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
    Check the connectivity status of the configured Instagram Business account.
    Uses graph.facebook.com/v21.0 — the correct endpoint for Business Content Publishing API.
    """
    return await service.check_status()


class InstagramReelPublishRequest(BaseModel):
    video_url: str
    caption: str
    thumbnail_url: Optional[str] = None


@router.post("/instagram/publish-reel")
async def publish_reel_to_instagram(
    request: InstagramReelPublishRequest,
    service: InstagramService = Depends(get_instagram_service)
):
    """
    Publish a video as an Instagram Reel.
    The video_url must be publicly accessible (e.g., the Railway static URL).
    """
    result = await service.publish_reel(
        video_url=request.video_url,
        caption=request.caption,
        thumbnail_url=request.thumbnail_url,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result)
    return result


class TestTokenRequest(BaseModel):
    platform: str
    access_token: str
    account_id: Optional[str] = None


@router.post("/test-token")
async def test_social_token(req: TestTokenRequest):
    """
    Live test a token against Meta Graph API and return account metadata without saving.
    """
    token = req.access_token.strip()
    if not token:
        raise HTTPException(status_code=400, detail="يرجى إدخال التوكن للاختبار")

    platform = req.platform.lower()

    if platform in ("instagram", "facebook"):
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                # 1. Test /me
                me_res = await client.get(
                    "https://graph.facebook.com/v21.0/me",
                    params={"fields": "id,name,instagram_business_account", "access_token": token}
                )
                me_data = me_res.json()
                if me_res.status_code != 200:
                    # Fallback: check if it is an Instagram User/Tester token directly from Instagram API Setup
                    ig_me_res = await client.get(
                        "https://graph.instagram.com/me",
                        params={"fields": "id,username,account_type", "access_token": token}
                    )
                    if ig_me_res.status_code == 200:
                        ig_data = ig_me_res.json()
                        return {
                            "valid": True,
                            "platform": platform,
                            "name": ig_data.get("username", "Instagram User"),
                            "id": ig_data.get("id"),
                            "pages": [],
                            "pages_count": 0,
                            "discovered_instagram_id": str(ig_data.get("id")),
                            "instagram_details": {
                                "id": ig_data.get("id"),
                                "username": ig_data.get("username"),
                                "account_type": ig_data.get("account_type")
                            }
                        }

                    err = me_data.get("error", {})
                    code = err.get("code", 0)
                    msg = err.get("message", "فشل التحقق من التوكن")
                    hint = "تأكد من نسخ التوكن كاملاً واختيار الصلاحيات المطلوبة."
                    if code == 190:
                        hint = "التوكن منتهي الصلاحية أو غير صالح — ولّد توكن جديد من Meta Graph API Explorer."
                    elif code == 10:
                        hint = "صلاحيات التطبيق غير كافية — تأكد من تفعيل صلاحيات instagram_business_basic و pages_read_engagement."
                    return {
                        "valid": False,
                        "error_code": code,
                        "message": msg,
                        "hint": hint,
                        "raw_error": err
                    }

                user_or_page_name = me_data.get("name", "")
                me_id = me_data.get("id", "")

                # 2. Query /me/accounts for pages
                pages_res = await client.get(
                    "https://graph.facebook.com/v21.0/me/accounts",
                    params={"fields": "id,name,instagram_business_account", "access_token": token}
                )
                pages = []
                auto_ig_id = None
                if pages_res.status_code == 200:
                    for p in pages_res.json().get("data", []):
                        ig = p.get("instagram_business_account")
                        pages.append({
                            "id": p.get("id"),
                            "name": p.get("name"),
                            "has_instagram": bool(ig),
                            "instagram_id": ig.get("id") if ig else None
                        })
                        if ig and not auto_ig_id:
                            auto_ig_id = str(ig.get("id"))

                # Also check if /me itself had instagram_business_account
                if not auto_ig_id and me_data.get("instagram_business_account"):
                    auto_ig_id = str(me_data["instagram_business_account"].get("id"))

                target_ig_id = req.account_id or auto_ig_id
                ig_account_details = None

                if target_ig_id:
                    ig_res = await client.get(
                        f"https://graph.facebook.com/v21.0/{target_ig_id}",
                        params={
                            "fields": "id,username,name,biography,followers_count,media_count",
                            "access_token": token
                        }
                    )
                    if ig_res.status_code == 200:
                        ig_account_details = ig_res.json()

                return {
                    "valid": True,
                    "platform": platform,
                    "name": user_or_page_name,
                    "id": me_id,
                    "pages": pages,
                    "pages_count": len(pages),
                    "discovered_instagram_id": target_ig_id,
                    "instagram_details": ig_account_details
                }
            except Exception as e:
                return {"valid": False, "message": f"حدث خطأ أثناء فحص التوكن: {str(e)}"}

    return {"valid": False, "message": f"فحص التوكن المباشر غير مدعوم لهذه المنصة حالياً: {platform}"}


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
