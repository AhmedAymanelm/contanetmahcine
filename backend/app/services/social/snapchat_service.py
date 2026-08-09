import logging
import httpx
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.oauth_token import OAuthToken

logger = logging.getLogger(__name__)

class SnapchatService:
    def __init__(self):
        self.client_id = settings.SNAPCHAT_CLIENT_ID
        self.client_secret = settings.SNAPCHAT_CLIENT_SECRET
        self.redirect_uri = settings.SNAPCHAT_REDIRECT_URI
        self.auth_url = "https://accounts.snapchat.com/login/oauth2/authorize"
        self.token_url = "https://accounts.snapchat.com/login/oauth2/access_token"
        
    def _is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.redirect_uri)
        
    def get_auth_url(self) -> str:
        if not self._is_configured():
            raise ValueError("Snapchat OAuth is not configured")
            
        from urllib.parse import urlencode
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "https://auth.snapchat.com/oauth2/api/user.display_name snapchat-profile-api snapchat-marketing-api"
        }
        return f"{self.auth_url}?{urlencode(params)}"
        
    async def exchange_code(self, code: str) -> dict:
        if not self._is_configured():
            return {"success": False, "message": "Snapchat OAuth not configured"}
            
        async with httpx.AsyncClient() as client:
            data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            try:
                res = await client.post(self.token_url, data=data)
                if res.status_code != 200:
                    logger.error(f"Snapchat Token Error: {res.text}")
                    return {"success": False, "message": f"Token exchange failed: {res.text}"}
                return {"success": True, "data": res.json()}
            except Exception as e:
                logger.error(f"Snapchat Code Exchange Exception: {e}")
                return {"success": False, "message": str(e)}

    def get_status(self, db: Session) -> dict:
        if not self._is_configured():
            return {"configured": False, "connected": False}
            
        token = db.query(OAuthToken).filter(OAuthToken.platform == "snapchat").first()
        if not token or not token.access_token:
            return {"configured": True, "connected": False}
            
        if token.expires_at and token.expires_at < datetime.utcnow():
            # In a real app we'd try to refresh the token here if we have a refresh_token
            return {"configured": True, "connected": False, "error": "Token expired"}
            
        return {
            "configured": True,
            "connected": True,
            "account_id": token.account_id,
            "expires_at": token.expires_at
        }
        
    def save_token(self, db: Session, token_data: dict, account_id: str = "snapchat_user"):
        token = db.query(OAuthToken).filter(OAuthToken.platform == "snapchat").first()
        if not token:
            token = OAuthToken(platform="snapchat")
            db.add(token)
            
        token.access_token = token_data.get("access_token")
        token.refresh_token = token_data.get("refresh_token")
        token.account_id = account_id
        
        expires_in = token_data.get("expires_in", 3600)
        token.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        db.commit()
