import httpx
from typing import Dict, Any, Optional
from app.core.config import settings

class FacebookService:
    def __init__(self):
        self.access_token = settings.FACEBOOK_ACCESS_TOKEN
        self.page_id = settings.FACEBOOK_PAGE_ID
        self.base_url = "https://graph.facebook.com/v19.0"

    def _is_configured(self) -> bool:
        return bool(self.access_token and self.page_id)

    async def check_status(self) -> Dict[str, Any]:
        if not self._is_configured():
            return {
                "connected": False,
                "error": "Facebook API credentials are not configured properly in .env"
            }
            
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/{self.page_id}",
                    params={
                        "fields": "id,name",
                        "access_token": self.access_token
                    }
                )
                
                data = response.json()
                if response.status_code == 200 and "id" in data:
                    return {
                        "connected": True,
                        "facebook_page_id": data.get("id"),
                        "name": data.get("name"),
                        "token_valid": True
                    }
                else:
                    return {
                        "connected": False,
                        "token_valid": False,
                        "error": data.get("error", {}).get("message", "Unknown error connecting to Facebook")
                    }
            except Exception as e:
                return {
                    "connected": False,
                    "error": str(e)
                }

    async def publish_image(self, image_url: str, caption: str) -> Dict[str, Any]:
        if not self._is_configured():
            return {
                "success": False,
                "platform": "facebook",
                "error": {
                    "code": "config_error",
                    "message": "Facebook API credentials are missing"
                }
            }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/{self.page_id}/photos",
                    params={
                        "url": image_url,
                        "message": caption,
                        "access_token": self.access_token
                    }
                )
                data = response.json()
                
                if response.status_code != 200 or "id" not in data:
                    return {
                        "success": False,
                        "platform": "facebook",
                        "error": {
                            "code": data.get("error", {}).get("code", "unknown"),
                            "message": data.get("error", {}).get("message", "Failed to publish photo to Facebook")
                        }
                    }
                    
                return {
                    "success": True,
                    "platform": "facebook",
                    "post_id": data["post_id"] if "post_id" in data else data["id"]
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "platform": "facebook",
                    "error": {
                        "code": "exception",
                        "message": str(e)
                    }
                }

    async def publish_text(self, text: str) -> Dict[str, Any]:
        if not self._is_configured():
            return {
                "success": False,
                "platform": "facebook",
                "error": {
                    "code": "config_error",
                    "message": "Facebook API credentials are missing"
                }
            }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/{self.page_id}/feed",
                    data={
                        "message": text,
                        "access_token": self.access_token
                    }
                )
                data = response.json()
                
                if response.status_code != 200 or "id" not in data:
                    return {
                        "success": False,
                        "platform": "facebook",
                        "error": {
                            "code": data.get("error", {}).get("code", "unknown"),
                            "message": data.get("error", {}).get("message", "Failed to publish text to Facebook")
                        }
                    }
                    
                return {
                    "success": True,
                    "platform": "facebook",
                    "post_id": data["id"]
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "platform": "facebook",
                    "error": {
                        "code": "exception",
                        "message": str(e)
                    }
                }

    async def publish_carousel(self, image_urls: list, caption: str) -> dict:
        if not self._is_configured():
            return {"success": False, "platform": "facebook", "error": {"code": "config_error", "message": "Facebook API credentials missing"}}
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                # 1. Upload photos as unpublished
                media_ids = []
                for url in image_urls:
                    res = await client.post(
                        f"{self.base_url}/{self.page_id}/photos",
                        params={
                            "url": url,
                            "published": "false",
                            "access_token": self.access_token
                        }
                    )
                    data = res.json()
                    if res.status_code != 200 or "id" not in data:
                        return {"success": False, "platform": "facebook", "error": {"code": "item_error", "message": str(data)}}
                    media_ids.append(data["id"])
                
                # 2. Publish post with attached media
                attached_media = {}
                for i, media_id in enumerate(media_ids):
                    attached_media[f"attached_media[{i}]"] = f'{{"media_fbid":"{media_id}"}}'
                
                params = {
                    "message": caption,
                    "access_token": self.access_token,
                    **attached_media
                }
                
                pub_res = await client.post(
                    f"{self.base_url}/{self.page_id}/feed",
                    data=params
                )
                pub_data = pub_res.json()
                if pub_res.status_code != 200 or "id" not in pub_data:
                    return {"success": False, "platform": "facebook", "error": {"code": "publish_error", "message": str(pub_data)}}
                
                return {"success": True, "platform": "facebook", "post_id": pub_data["id"]}
            except Exception as e:
                return {"success": False, "platform": "facebook", "error": {"code": "exception", "message": str(e)}}
