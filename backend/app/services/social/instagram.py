"""
Instagram Business Graph API Service
Uses graph.facebook.com/v21.0 — the correct endpoint for Instagram Business Content Publishing API.

Required settings:
  INSTAGRAM_ACCESS_TOKEN  — a long-lived Page Access Token (or User Access Token with page permissions)
  INSTAGRAM_ACCOUNT_ID   — the Instagram Business/Creator Account ID (not the Facebook Page ID)

How to get credentials:
  1. Go to Meta for Developers → your app → Instagram section
  2. Connect your Facebook Page that is linked to the IG Business account
  3. Generate a long-lived Page Access Token
  4. Get your Instagram Business Account ID via:
     GET https://graph.facebook.com/v21.0/me/accounts?access_token=<PAGE_TOKEN>
     Then GET https://graph.facebook.com/v21.0/{page-id}?fields=instagram_business_account&access_token=<TOKEN>
"""
import httpx
from typing import Dict, Any, Optional
from app.core.config import settings


class InstagramService:
    # Use graph.facebook.com (not graph.instagram.com) for Business Content Publishing API
    API_VERSION = "v21.0"

    def __init__(self):
        self.access_token = settings.INSTAGRAM_ACCESS_TOKEN
        self.account_id = settings.INSTAGRAM_ACCOUNT_ID
        # Correct base URL for Instagram Business Graph API
        self.base_url = f"https://graph.facebook.com/{self.API_VERSION}"

    def _is_configured(self) -> bool:
        return bool(self.access_token and self.account_id)

    async def _auto_discover_and_save_account_id(self) -> Optional[str]:
        """
        Attempts to automatically discover the Instagram Business Account ID
        from the access token via Facebook Graph API.
        """
        token = self.access_token or getattr(settings, "FACEBOOK_ACCESS_TOKEN", None)
        if not token:
            return None

        async with httpx.AsyncClient(timeout=12.0) as client:
            try:
                # 1. Try /me?fields=id,name,instagram_business_account (works if token is Page Access Token)
                res = await client.get(
                    f"{self.base_url}/me",
                    params={"fields": "id,name,instagram_business_account", "access_token": token}
                )
                if res.status_code == 200:
                    data = res.json()
                    ig = data.get("instagram_business_account")
                    if isinstance(ig, dict) and ig.get("id"):
                        account_id = str(ig["id"])
                        self._persist_account_id(account_id)
                        return account_id

                # 2. Try /me/accounts?fields=id,name,instagram_business_account (works if token is User Access Token)
                res = await client.get(
                    f"{self.base_url}/me/accounts",
                    params={"fields": "id,name,instagram_business_account", "access_token": token}
                )
                if res.status_code == 200:
                    data = res.json()
                    pages = data.get("data", [])
                    for page in pages:
                        ig = page.get("instagram_business_account")
                        if isinstance(ig, dict) and ig.get("id"):
                            account_id = str(ig["id"])
                            self._persist_account_id(account_id)
                            return account_id
            except Exception:
                pass
        return None

    def _persist_account_id(self, account_id: str):
        self.account_id = account_id
        try:
            setattr(settings, "INSTAGRAM_ACCOUNT_ID", account_id)
            from app.db.session import SessionLocal
            from app.models.app_setting import AppSetting
            db = SessionLocal()
            try:
                setting = db.query(AppSetting).filter(AppSetting.key == "INSTAGRAM_ACCOUNT_ID").first()
                if not setting:
                    setting = AppSetting(key="INSTAGRAM_ACCOUNT_ID", value=account_id)
                    db.add(setting)
                else:
                    setting.value = account_id
                db.commit()
            finally:
                db.close()
        except Exception:
            pass

    async def check_status(self) -> Dict[str, Any]:
        # Fallback to Facebook token if Instagram token not set
        if not self.access_token and getattr(settings, "FACEBOOK_ACCESS_TOKEN", None):
            self.access_token = settings.FACEBOOK_ACCESS_TOKEN

        if not self.access_token:
            return {
                "connected": False,
                "error": "لم يتم إدخال INSTAGRAM_ACCESS_TOKEN. يرجى إدخال التوكن في إعدادات الربط.",
                "hint": "اذهب إلى إعدادات الربط والـ API → Instagram → أدخل التوكن"
            }

        # If account_id is not set, try auto-discovery
        if not self.account_id:
            discovered = await self._auto_discover_and_save_account_id()
            if discovered:
                self.account_id = discovered

        if not self.account_id:
            # We have a token but couldn't auto-discover account ID.
            # Make a diagnostic call to /me to see why or check token validity
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    me_res = await client.get(
                        f"{self.base_url}/me",
                        params={"fields": "id,name", "access_token": self.access_token}
                    )
                    me_data = me_res.json()
                    if me_res.status_code != 200:
                        err = me_data.get("error", {})
                        err_code = err.get("code", 0)
                        if err_code == 190:
                            return {
                                "connected": False,
                                "error": "التوكن منتهي الصلاحية أو غير صالح (Session expired). يرجى تجديد التوكن من Meta Graph API Explorer.",
                                "token_valid": False,
                            }
                        return {
                            "connected": False,
                            "error": f"التوكن غير صالح: {err.get('message', 'خطأ غير معروف')}",
                            "token_valid": False,
                        }
                    else:
                        token_name = me_data.get("name", "غير محدد")
                        return {
                            "connected": False,
                            "token_valid": True,
                            "error": f"التوكن صالح باسم ({token_name}) ولكن لم يتم العثور على حساب Instagram Business تلقائياً. أدخل INSTAGRAM_ACCOUNT_ID يدوياً أو تأكد من ربط صفحة الفيسبوك بحساب إنستغرام للأعمال.",
                            "hint": "أدخل INSTAGRAM_ACCOUNT_ID في إعدادات الربط"
                        }
            except Exception as e:
                return {
                    "connected": False,
                    "error": f"خطأ في الاتصال مع Meta: {str(e)}"
                }

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                # Verify the Instagram Business Account using the correct endpoint
                response = await client.get(
                    f"{self.base_url}/{self.account_id}",
                    params={
                        "fields": "id,username,name,biography,followers_count,media_count",
                        "access_token": self.access_token
                    }
                )

                data = response.json()

                if response.status_code == 200 and "id" in data:
                    return {
                        "connected": True,
                        "instagram_account_id": data.get("id"),
                        "username": data.get("username"),
                        "name": data.get("name"),
                        "followers": data.get("followers_count", 0),
                        "media_count": data.get("media_count", 0),
                        "token_valid": True,
                        "api_version": self.API_VERSION,
                    }
                else:
                    error_msg = "Unknown error"
                    if isinstance(data.get("error"), dict):
                        err = data["error"]
                        error_code = err.get("code", 0)
                        # Provide helpful guidance based on error code
                        if error_code == 190:
                            error_msg = "التوكن منتهي أو غير صالح — يجب تجديد Long-Lived Token من Meta"
                        elif error_code in (100, 803):
                            error_msg = f"رقم الحساب ({self.account_id}) غير صحيح أو غير مرتبط بهذا التوكن — تحقق من INSTAGRAM_ACCOUNT_ID"
                        elif error_code == 10:
                            error_msg = "صلاحيات التطبيق غير كافية — تأكد من تفعيل صلاحية instagram_business_basic"
                        else:
                            error_msg = f"خطأ Meta ({error_code}): {err.get('message', '')}"
                    return {
                        "connected": False,
                        "token_valid": False,
                        "error": error_msg,
                        "raw_error": data.get("error"),
                    }
            except Exception as e:
                return {
                    "connected": False,
                    "error": f"Connection error: {str(e)}"
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

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                # Step 1: Create Media Container
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

                # Step 2: Poll container status until FINISHED
                import asyncio
                max_attempts = 20
                is_finished = False
                for attempt in range(max_attempts):
                    status_response = await client.get(
                        f"{self.base_url}/{creation_id}",
                        params={
                            "fields": "status_code,status",
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
                                "message": f"Media container failed: {status_code} — {status_data.get('status', '')}"
                            }
                        }
                    await asyncio.sleep(3)

                if not is_finished:
                    return {
                        "success": False,
                        "platform": "instagram",
                        "error": {
                            "code": "timeout",
                            "message": "Media container processing timed out after 60s."
                        }
                    }

                # Step 3: Publish Media Container
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

    async def publish_reel(self, video_url: str, caption: str, thumbnail_url: str = None) -> Dict[str, Any]:
        """Publish a video as an Instagram Reel via the Content Publishing API."""
        if not self._is_configured():
            return {"success": False, "platform": "instagram", "error": {"code": "config_error", "message": "Instagram API credentials missing"}}

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                import asyncio
                # Step 1: Create Reel container
                params = {
                    "media_type": "REELS",
                    "video_url": video_url,
                    "caption": caption,
                    "access_token": self.access_token
                }
                if thumbnail_url:
                    params["thumbnail_url"] = thumbnail_url

                create_res = await client.post(
                    f"{self.base_url}/{self.account_id}/media",
                    params=params
                )
                create_data = create_res.json()

                if create_res.status_code != 200 or "id" not in create_data:
                    return {"success": False, "platform": "instagram", "error": {"code": create_data.get("error", {}).get("code", "unknown"), "message": create_data.get("error", {}).get("message", "Failed to create reel container")}}

                creation_id = create_data["id"]

                # Step 2: Poll until FINISHED (videos take longer)
                max_attempts = 30
                is_finished = False
                for _ in range(max_attempts):
                    st_res = await client.get(
                        f"{self.base_url}/{creation_id}",
                        params={"fields": "status_code,status", "access_token": self.access_token}
                    )
                    st_data = st_res.json()
                    code = st_data.get("status_code", "")
                    if code == "FINISHED":
                        is_finished = True
                        break
                    elif code in ["ERROR", "EXPIRED"]:
                        return {"success": False, "platform": "instagram", "error": {"code": "reel_error", "message": f"Reel container failed: {code}"}}
                    await asyncio.sleep(4)

                if not is_finished:
                    return {"success": False, "platform": "instagram", "error": {"code": "timeout", "message": "Reel processing timed out"}}

                # Step 3: Publish
                pub_res = await client.post(
                    f"{self.base_url}/{self.account_id}/media_publish",
                    params={"creation_id": creation_id, "access_token": self.access_token}
                )
                pub_data = pub_res.json()

                if pub_res.status_code != 200 or "id" not in pub_data:
                    return {"success": False, "platform": "instagram", "error": {"code": pub_data.get("error", {}).get("code", "publish_error"), "message": pub_data.get("error", {}).get("message", "Failed to publish reel")}}

                return {"success": True, "platform": "instagram", "media_id": pub_data["id"], "type": "reel"}

            except Exception as e:
                return {"success": False, "platform": "instagram", "error": {"code": "exception", "message": str(e)}}

    async def publish_carousel(self, image_urls: list, caption: str) -> dict:
        """Publish a carousel (album) post to Instagram."""
        if not self._is_configured():
            return {"success": False, "platform": "instagram", "error": {"code": "config_error", "message": "Instagram API credentials missing"}}

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                import asyncio
                # Step 1: Create item containers
                child_ids = []
                for url in image_urls[:10]:  # Instagram max 10 images
                    create_res = await client.post(
                        f"{self.base_url}/{self.account_id}/media",
                        params={"image_url": url, "is_carousel_item": "true", "access_token": self.access_token}
                    )
                    data = create_res.json()
                    if create_res.status_code != 200 or "id" not in data:
                        return {"success": False, "platform": "instagram", "error": {"code": "item_error", "message": str(data)}}
                    child_ids.append(data["id"])

                # Step 2: Create Carousel Container
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

                # Step 3: Poll Carousel Container Status
                max_attempts = 20
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

                # Step 4: Publish
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
