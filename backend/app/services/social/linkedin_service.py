import logging
import httpx
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.oauth_token import OAuthToken

logger = logging.getLogger(__name__)

class LinkedInService:
    def __init__(self):
        self.client_id = settings.LINKEDIN_CLIENT_ID
        self.client_secret = settings.LINKEDIN_CLIENT_SECRET
        self.redirect_uri = settings.LINKEDIN_REDIRECT_URI
        self.auth_url = "https://www.linkedin.com/oauth/v2/authorization"
        self.token_url = "https://www.linkedin.com/oauth/v2/accessToken"
        self.api_url = "https://api.linkedin.com/v2"

    def _is_configured(self):
        return bool(self.client_id and self.client_secret and self.redirect_uri)

    def generate_auth_url(self) -> str:
        if not self._is_configured():
            raise ValueError("LinkedIn API is not fully configured in settings.")
        
        from urllib.parse import urlencode
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "w_member_social openid profile email"
        }
        return f"{self.auth_url}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict:
        """Exchanges the authorization code for an access token."""
        async with httpx.AsyncClient() as client:
            payload = {
                "grant_type": "authorization_code",
                "code": code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": self.redirect_uri
            }
            res = await client.post(self.token_url, data=payload)
            if res.status_code != 200:
                logger.error(f"Failed to exchange LinkedIn code: {res.text}")
                return {"success": False, "error": res.json() if res.text else "Unknown error"}
            
            return {"success": True, "data": res.json()}

    async def get_user_profile(self, access_token: str) -> dict:
        """Fetches basic profile info using OpenID userinfo."""
        url = "https://api.linkedin.com/v2/userinfo"
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            res = await client.get(url, headers=headers)
            if res.status_code != 200:
                logger.error(f"Failed to fetch LinkedIn profile: {res.text}")
                return {"success": False, "error": res.json() if res.text else "Unknown error"}
            
            return {"success": True, "data": res.json()}

    async def publish_media(self, text: str, file_paths: list, media_type: str, access_token: str, person_urn: str) -> dict:
        """Publishes a media post (multiple images or single document) to LinkedIn."""
        logger.info(f"LINKEDIN PUBLISH MEDIA CALLED! file_paths={file_paths}, media_type={media_type}")
        recipe = "urn:li:digitalmediaRecipe:feedshare-image" if media_type == "IMAGE" else "urn:li:digitalmediaRecipe:feedshare-document"
        register_url = f"{self.api_url}/assets?action=registerUpload"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
            "Linkedin-Version": "202401"
        }
        
        asset_urns = []
        async with httpx.AsyncClient(timeout=60.0) as client:
            for file_path in file_paths:
                register_payload = {
                    "registerUploadRequest": {
                        "recipes": [recipe],
                        "owner": f"urn:li:person:{person_urn}",
                        "serviceRelationships": [{"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}]
                    }
                }
                
                reg_res = await client.post(register_url, json=register_payload, headers=headers)
                if reg_res.status_code != 200:
                    logger.error(f"Failed to register LinkedIn upload: {reg_res.text}")
                    return await self.publish_text(text, access_token, person_urn)
                
                reg_data = reg_res.json()
                upload_url = reg_data["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
                asset_urn = reg_data["value"]["asset"]
                
                # 2. Upload Binary
                with open(file_path, 'rb') as f:
                    file_data = f.read()
                
                upload_headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/octet-stream"}
                upload_res = await client.put(upload_url, content=file_data, headers=upload_headers)
                if upload_res.status_code not in (200, 201):
                    logger.error(f"Failed to upload LinkedIn binary: {upload_res.text}")
                    return await self.publish_text(text, access_token, person_urn)
                
                asset_urns.append(asset_urn)

            # 3. Create UGC Post
            post_url = f"{self.api_url}/ugcPosts"
            media_attachments = []
            for urn in asset_urns:
                att = {
                    "status": "READY",
                    "media": urn
                }
                if media_type == "DOCUMENT":
                    att["title"] = {"text": "Media attachment"}
                media_attachments.append(att)

            post_payload = {
                "author": f"urn:li:person:{person_urn}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": text},
                        "shareMediaCategory": media_type,
                        "media": media_attachments
                    }
                },
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
            }

            res = await client.post(post_url, json=post_payload, headers=headers)
            if res.status_code not in (200, 201):
                logger.error(f"Failed to publish LinkedIn media post: {res.text}")
                return {"success": False, "error": res.json() if res.text else "Unknown error"}
            
            return {"success": True, "data": res.json()}

    async def publish_text(self, text: str, access_token: str, person_urn: str) -> dict:
        """Publishes a text post to LinkedIn."""
        url = f"{self.api_url}/ugcPosts"
        async with httpx.AsyncClient(timeout=60.0) as client:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "X-Restli-Protocol-Version": "2.0.0",
                "Content-Type": "application/json",
                "Linkedin-Version": "202401"
            }
            payload = {
                "author": f"urn:li:person:{person_urn}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": text
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
            res = await client.post(url, json=payload, headers=headers)
            if res.status_code not in (200, 201):
                logger.error(f"Failed to publish to LinkedIn: {res.text}")
                return {"success": False, "error": res.json() if res.text else "Unknown error"}
            
            return {"success": True, "data": res.json()}

    def get_status(self, db: Session) -> dict:
        """Checks if LinkedIn is connected and token is available."""
        if not self._is_configured():
            return {"configured": False, "connected": False}
            
        token_entry = db.query(OAuthToken).filter(OAuthToken.platform == "linkedin").first()
        if token_entry and token_entry.access_token:
            return {
                "configured": True, 
                "connected": True, 
                "account_id": token_entry.account_id,
                "expires_at": token_entry.expires_at
            }
        
        return {"configured": True, "connected": False}
