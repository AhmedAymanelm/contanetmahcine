import logging
import httpx
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.oauth_token import OAuthToken

logger = logging.getLogger(__name__)

class ThreadsService:
    def __init__(self):
        self.app_id = settings.THREADS_CLIENT_ID
        self.app_secret = settings.THREADS_CLIENT_SECRET
        self.redirect_uri = settings.THREADS_REDIRECT_URI
        self.base_url = "https://graph.threads.net/v1.0"
        self.oauth_url = "https://threads.net/oauth/authorize"
        self.token_url = "https://graph.threads.net/oauth/access_token"

    def _is_configured(self):
        return bool(self.app_id and self.app_secret and self.redirect_uri)

    def generate_auth_url(self) -> str:
        if not (self.app_id and self.redirect_uri):
            raise ValueError("Threads API is not fully configured in settings (Missing Client ID or Redirect URI).")
        
        from urllib.parse import urlencode
        # Scopes required for posting and reading
        params = {
            "client_id": self.app_id,
            "redirect_uri": self.redirect_uri,
            "scope": "threads_basic,threads_content_publish",
            "response_type": "code"
        }
        return f"{self.oauth_url}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict:
        """Exchanges the authorization code for a short-lived access token."""
        async with httpx.AsyncClient() as client:
            payload = {
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "grant_type": "authorization_code",
                "redirect_uri": self.redirect_uri,
                "code": code
            }
            res = await client.post(self.token_url, data=payload)
            if res.status_code != 200:
                logger.error(f"Failed to exchange code: {res.text}")
                return {"success": False, "error": res.json()}
            
            return {"success": True, "data": res.json()}

    async def get_long_lived_token(self, short_token: str) -> dict:
        """Exchanges a short-lived token for a long-lived one (60 days)."""
        url = f"{self.base_url}/access_token"
        async with httpx.AsyncClient() as client:
            params = {
                "grant_type": "th_exchange_token",
                "client_secret": self.app_secret,
                "access_token": short_token
            }
            res = await client.get(url, params=params)
            if res.status_code != 200:
                logger.error(f"Failed to get long-lived token: {res.text}")
                return {"success": False, "error": res.json()}
            
            return {"success": True, "data": res.json()}

    async def refresh_long_lived_token(self, long_token: str) -> dict:
        """Refreshes an unexpired long-lived token."""
        url = f"{self.base_url}/refresh_access_token"
        async with httpx.AsyncClient() as client:
            params = {
                "grant_type": "th_refresh_token",
                "access_token": long_token
            }
            res = await client.get(url, params=params)
            if res.status_code != 200:
                logger.error(f"Failed to refresh long-lived token: {res.text}")
                return {"success": False, "error": res.json()}
            
            return {"success": True, "data": res.json()}

    async def get_user_profile(self, access_token: str) -> dict:
        """Fetches basic profile info (id, username)."""
        url = f"{self.base_url}/me"
        async with httpx.AsyncClient() as client:
            params = {
                "fields": "id,username,name,threads_profile_picture_url",
                "access_token": access_token
            }
            res = await client.get(url, params=params)
            if res.status_code != 200:
                logger.error(f"Failed to fetch profile: {res.text}")
                return {"success": False, "error": res.json()}
            
            return {"success": True, "data": res.json()}

    async def publish_text(self, text: str, access_token: str, user_id: str) -> dict:
        """Publishes text to Threads in two steps: create container -> publish container."""
        # 1. Create Media Container
        create_url = f"{self.base_url}/{user_id}/threads"
        async with httpx.AsyncClient() as client:
            create_payload = {
                "media_type": "TEXT",
                "text": text,
                "access_token": access_token
            }
            create_res = await client.post(create_url, data=create_payload)
            if create_res.status_code != 200:
                logger.error(f"Failed to create Threads media container: {create_res.text}")
                return {"success": False, "error": create_res.json()}
            
            container_id = create_res.json().get("id")
            if not container_id:
                return {"success": False, "error": "No container ID returned"}

            # 2. Publish Container
            publish_url = f"{self.base_url}/{user_id}/threads_publish"
            publish_payload = {
                "creation_id": container_id,
                "access_token": access_token
            }
            pub_res = await client.post(publish_url, data=publish_payload)
            if pub_res.status_code != 200:
                logger.error(f"Failed to publish Threads media container: {pub_res.text}")
                return {"success": False, "error": pub_res.json()}
            
            return {"success": True, "data": pub_res.json()}

    async def check_and_refresh_token(self, db: Session) -> str:
        """Retrieves the token from the DB. Refreshes if needed."""
        token_entry = db.query(OAuthToken).filter(OAuthToken.platform == "threads").first()
        if not token_entry:
            return None
        
        # If token expires in less than 5 days, refresh it
        if token_entry.expires_at and (token_entry.expires_at - datetime.utcnow()).days < 5:
            refresh_res = await self.refresh_long_lived_token(token_entry.access_token)
            if refresh_res.get("success"):
                new_token = refresh_res["data"]["access_token"]
                expires_in = refresh_res["data"].get("expires_in", 5184000) # Default 60 days
                token_entry.access_token = new_token
                token_entry.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                db.commit()
                return new_token
            else:
                logger.error("Failed to auto-refresh Threads token")
        
        return token_entry.access_token

    def get_status(self, db: Session) -> dict:
        """Checks if Threads is connected and the token is available."""
        if not self._is_configured():
            return {"configured": False, "connected": False}
            
        token_entry = db.query(OAuthToken).filter(OAuthToken.platform == "threads").first()
        if token_entry and token_entry.access_token:
            return {
                "configured": True, 
                "connected": True, 
                "account_id": token_entry.account_id,
                "expires_at": token_entry.expires_at
            }
        
        return {"configured": True, "connected": False}
