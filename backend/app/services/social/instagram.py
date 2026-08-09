import httpx
from typing import Dict, Any, Optional
from app.core.config import settings

class InstagramService:
    def __init__(self):
        self.access_token = settings.INSTAGRAM_ACCESS_TOKEN
        self.account_id = settings.INSTAGRAM_ACCOUNT_ID
        self.base_url = "https://graph.instagram.com/v19.0"

    def _is_configured(self) -> bool:
        return bool(self.access_token and self.account_id)

    async def check_status(self) -> Dict[str, Any]:
        if not self._is_configured():
            return {
                "connected": False,
                "error": "Instagram API credentials are not configured properly in .env"
            }
            
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/{self.account_id}",
                    params={
                        "fields": "id,username",
                        "access_token": self.access_token
                    }
                )
                
                data = response.json()
                if response.status_code == 200 and "id" in data:
                    return {
                        "connected": True,
                        "instagram_account_id": data.get("id"),
                        "username": data.get("username"),
                        "token_valid": True
                    }
                else:
                    return {
                        "connected": False,
                        "token_valid": False,
                        "error": data.get("error", {}).get("message", "Unknown error connecting to Instagram")
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
                "platform": "instagram",
                "error": {
                    "code": "config_error",
                    "message": "Instagram API credentials are missing"
                }
            }

        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. Create Media Container
            try:
                create_response = await client.post(
                    f"{self.base_url}/{self.account_id}/media",
                    params={
                        "image_url": image_url,
                        "caption": caption,
                        "access_token": self.access_token
                    }
                )
                create_data = create_response.json()
                
                if create_response.status_code != 200 or "id" not in create_data:
                    return {
                        "success": False,
                        "platform": "instagram",
                        "error": {
                            "code": create_data.get("error", {}).get("code", "unknown"),
                            "message": create_data.get("error", {}).get("message", "Failed to create media container")
                        }
                    }
                    
                creation_id = create_data["id"]
                
                # Polling for container status
                import asyncio
                max_attempts = 15
                is_finished = False
                for attempt in range(max_attempts):
                    status_response = await client.get(
                        f"{self.base_url}/{creation_id}",
                        params={
                            "fields": "status_code",
                            "access_token": self.access_token
                        }
                    )
                    status_data = status_response.json()
                    status_code = status_data.get("status_code", "")
                    
                    if status_code == "FINISHED":
                        is_finished = True
                        break
                    elif status_code in ["ERROR", "EXPIRED"]:
                        return {
                            "success": False,
                            "platform": "instagram",
                            "error": {
                                "code": "container_error",
                                "message": f"Media container failed to process: {status_code}"
                            }
                        }
                    await asyncio.sleep(2)
                
                if not is_finished:
                    return {
                        "success": False,
                        "platform": "instagram",
                        "error": {
                            "code": "timeout",
                            "message": "Media container processing timed out."
                        }
                    }
                
                # 2. Publish Media Container
                publish_response = await client.post(
                    f"{self.base_url}/{self.account_id}/media_publish",
                    params={
                        "creation_id": creation_id,
                        "access_token": self.access_token
                    }
                )
                publish_data = publish_response.json()
                
                if publish_response.status_code != 200 or "id" not in publish_data:
                    return {
                        "success": False,
                        "platform": "instagram",
                        "error": {
                            "code": publish_data.get("error", {}).get("code", "unknown"),
                            "message": publish_data.get("error", {}).get("message", "Failed to publish media container")
                        }
                    }
                    
                return {
                    "success": True,
                    "platform": "instagram",
                    "media_id": publish_data["id"]
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "platform": "instagram",
                    "error": {
                        "code": "exception",
                        "message": str(e)
                    }
                }

    async def publish_carousel(self, image_urls: list, caption: str) -> dict:
        if not self._is_configured():
            return {"success": False, "platform": "instagram", "error": {"code": "config_error", "message": "Instagram API credentials missing"}}
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                import asyncio
                # 1. Create item containers
                child_ids = []
                for url in image_urls[:10]: # Instagram limit is 10
                    create_res = await client.post(
                        f"{self.base_url}/{self.account_id}/media",
                        params={"image_url": url, "is_carousel_item": "true", "access_token": self.access_token}
                    )
                    data = create_res.json()
                    if create_res.status_code != 200 or "id" not in data:
                        return {"success": False, "platform": "instagram", "error": {"code": "item_error", "message": str(data)}}
                    child_ids.append(data["id"])
                
                # 2. Create Carousel Container
                car_res = await client.post(
                    f"{self.base_url}/{self.account_id}/media",
                    params={
                        "media_type": "CAROUSEL",
                        "children": ",".join(child_ids),
                        "caption": caption,
                        "access_token": self.access_token
                    }
                )
                car_data = car_res.json()
                if car_res.status_code != 200 or "id" not in car_data:
                    return {"success": False, "platform": "instagram", "error": {"code": "carousel_error", "message": str(car_data)}}
                creation_id = car_data["id"]
                
                # 3. Poll Carousel Container Status
                max_attempts = 15
                is_finished = False
                for _ in range(max_attempts):
                    status_res = await client.get(
                        f"{self.base_url}/{creation_id}",
                        params={"fields": "status_code", "access_token": self.access_token}
                    )
                    st_data = status_res.json()
                    status_code = st_data.get("status_code", "")
                    if status_code == "FINISHED":
                        is_finished = True
                        break
                    elif status_code in ["ERROR", "EXPIRED"]:
                        return {"success": False, "platform": "instagram", "error": {"code": "container_error", "message": f"Carousel failed: {status_code}"}}
                    await asyncio.sleep(2.5)
                
                if not is_finished:
                    return {"success": False, "platform": "instagram", "error": {"code": "timeout", "message": "Carousel processing timed out"}}
                
                # 4. Publish
                pub_res = await client.post(
                    f"{self.base_url}/{self.account_id}/media_publish",
                    params={"creation_id": creation_id, "access_token": self.access_token}
                )
                pub_data = pub_res.json()
                if pub_res.status_code != 200 or "id" not in pub_data:
                    return {"success": False, "platform": "instagram", "error": {"code": "publish_error", "message": str(pub_data)}}
                
                return {"success": True, "platform": "instagram", "media_id": pub_data["id"]}
            except Exception as e:
                return {"success": False, "platform": "instagram", "error": {"code": "exception", "message": str(e)}}
