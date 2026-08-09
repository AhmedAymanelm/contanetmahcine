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

    async def publish_text(self, text: str, access_token: str, person_urn: str) -> dict:
        """Publishes a text post to LinkedIn."""
        url = f"{self.api_url}/ugcPosts"
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "X-Restli-Protocol-Version": "2.0.0",
                "Content-Type": "application/json"
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
