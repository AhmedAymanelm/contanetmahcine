"""
TikTok OAuth 2.0 + Content Posting API service.

Secrets (client_secret, access_token, refresh_token, auth codes) are NEVER logged.
"""
import logging
import secrets
import httpx
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from urllib.parse import urlencode
from app.core.config import settings
from app.models.oauth_token import OAuthToken

logger = logging.getLogger(__name__)

# ─── TikTok API constants ─────────────────────────────────────────────────────
TIKTOK_AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
TIKTOK_CREATOR_INFO_URL = "https://open.tiktokapis.com/v2/post/publish/creator_info/query/"
TIKTOK_VIDEO_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"

# Scopes required:
#   user.info.basic  – read basic profile (open_id, display_name)
#   video.upload     – upload video bytes
#   video.publish    – publish to feed (requires TikTok app review/approval)
TIKTOK_SCOPES = "user.info.basic,video.upload,video.publish"

# Simple in-process state store (one node only; fine for Railway single-replica).
# For multi-replica deployments, replace with Redis or DB-backed store.
_oauth_states: dict[str, datetime] = {}
_STATE_TTL_SECONDS = 600  # 10 minutes


class TikTokService:
    """Handles TikTok OAuth 2.0 Web Login and Content Posting API."""

    def __init__(self):
        self.client_key = settings.TIKTOK_CLIENT_KEY
        self.client_secret = settings.TIKTOK_CLIENT_SECRET
        self.redirect_uri = settings.TIKTOK_REDIRECT_URI

    # ── Configuration helpers ─────────────────────────────────────────────────

    def _is_configured(self) -> bool:
        return bool(self.client_key and self.client_secret and self.redirect_uri)

    def _require_configured(self):
        if not self._is_configured():
            raise ValueError(
                "TikTok integration is not configured. "
                "Set TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, and TIKTOK_REDIRECT_URI."
            )

    # ── OAuth state management ────────────────────────────────────────────────

    def generate_state(self) -> str:
        """Generate a cryptographically random state value and cache it."""
        state = secrets.token_urlsafe(32)
        _oauth_states[state] = datetime.utcnow()
        # Prune expired states to avoid unbounded growth
        expired = [k for k, v in _oauth_states.items()
                   if (datetime.utcnow() - v).total_seconds() > _STATE_TTL_SECONDS]
        for k in expired:
            del _oauth_states[k]
        return state

    def validate_state(self, state: str) -> bool:
        """Validate and consume a state value (one-time use)."""
        created_at = _oauth_states.pop(state, None)
        if created_at is None:
            return False
        if (datetime.utcnow() - created_at).total_seconds() > _STATE_TTL_SECONDS:
            return False
        return True

    # ── OAuth 2.0 Login ───────────────────────────────────────────────────────

    def generate_auth_url(self) -> tuple[str, str]:
        """Build TikTok OAuth v2 authorization URL. Returns (url, state)."""
        self._require_configured()
        state = self.generate_state()
        params = {
            "client_key": self.client_key,
            "response_type": "code",
            "scope": TIKTOK_SCOPES,
            "redirect_uri": self.redirect_uri,
            "state": state,
        }
        url = f"{TIKTOK_AUTH_URL}?{urlencode(params)}"
        logger.info("Generated TikTok OAuth URL (state omitted from log)")
        return url, state

    # ── Token exchange ────────────────────────────────────────────────────────

    async def exchange_code(self, code: str) -> dict:
        """Exchange authorization code for access + refresh tokens."""
        self._require_configured()
        payload = {
            "client_key": self.client_key,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(TIKTOK_TOKEN_URL, data=payload, headers=headers)

        if res.status_code != 200:
            logger.error(f"TikTok token exchange failed: status={res.status_code}")
            return {"success": False, "error": "Token exchange failed", "detail": res.text}

        data = res.json()
        if data.get("error"):
            logger.error(f"TikTok token exchange error: {data.get('error_description', data.get('error'))}")
            return {"success": False, "error": data.get("error"), "detail": data.get("error_description")}

        return {"success": True, "data": data}

    # ── Token refresh ─────────────────────────────────────────────────────────

    async def refresh_access_token(self, refresh_token: str) -> dict:
        """Use refresh_token to obtain a new access_token."""
        self._require_configured()
        payload = {
            "client_key": self.client_key,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(TIKTOK_TOKEN_URL, data=payload, headers=headers)

        if res.status_code != 200:
            logger.error(f"TikTok token refresh failed: status={res.status_code}")
            return {"success": False, "error": "Token refresh failed"}

        data = res.json()
        if data.get("error"):
            logger.error(f"TikTok refresh error: {data.get('error')}")
            return {"success": False, "error": data.get("error"), "detail": data.get("error_description")}

        return {"success": True, "data": data}

    # ── DB helpers ────────────────────────────────────────────────────────────

    def save_token(self, db: Session, token_data: dict) -> OAuthToken:
        """Upsert TikTok token row. Never logs access/refresh tokens."""
        open_id = token_data.get("open_id", "")
        access_token = token_data.get("access_token", "")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 86400)
        refresh_expires_in = token_data.get("refresh_expires_in", 31536000)
        scopes = token_data.get("scope", "")

        entry = db.query(OAuthToken).filter(OAuthToken.platform == "tiktok").first()
        if not entry:
            entry = OAuthToken(platform="tiktok")
            db.add(entry)

        entry.access_token = access_token
        entry.refresh_token = refresh_token
        entry.account_id = open_id
        entry.open_id = open_id
        entry.scopes = scopes
        entry.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        entry.refresh_expires_at = datetime.utcnow() + timedelta(seconds=refresh_expires_in)

        db.commit()
        db.refresh(entry)
        logger.info(f"Saved TikTok token for open_id={open_id} (token values not logged)")
        return entry

    def get_token_entry(self, db: Session) -> OAuthToken | None:
        return db.query(OAuthToken).filter(OAuthToken.platform == "tiktok").first()

    async def get_valid_access_token(self, db: Session) -> str | None:
        """Return a valid access token, refreshing if necessary."""
        entry = self.get_token_entry(db)
        if not entry:
            return None

        # Check if access token is still valid (with 5-min buffer)
        if entry.expires_at and datetime.utcnow() < entry.expires_at - timedelta(minutes=5):
            return entry.access_token

        # Try refresh
        if not entry.refresh_token:
            logger.warning("TikTok access token expired and no refresh token available")
            return None

        # Check refresh token expiry
        if entry.refresh_expires_at and datetime.utcnow() > entry.refresh_expires_at:
            logger.warning("TikTok refresh token has also expired — re-auth required")
            return None

        logger.info("TikTok access token expired, refreshing...")
        refresh_res = await self.refresh_access_token(entry.refresh_token)
        if not refresh_res.get("success"):
            logger.error(f"TikTok token refresh failed: {refresh_res.get('error')}")
            return None

        self.save_token(db, refresh_res["data"])
        return refresh_res["data"].get("access_token")

    def get_status(self, db: Session) -> dict:
        """Return safe connection status (no tokens)."""
        entry = self.get_token_entry(db)
        if not entry:
            return {"connected": False}

        is_expired = (
            entry.expires_at is not None
            and datetime.utcnow() > entry.expires_at
        )
        refresh_expired = (
            entry.refresh_expires_at is not None
            and datetime.utcnow() > entry.refresh_expires_at
        )
        scopes = entry.scopes.split(",") if entry.scopes else []

        return {
            "connected": True,
            "open_id": entry.open_id or entry.account_id,
            "scopes": scopes,
            "access_token_expired": is_expired,
            "refresh_token_expired": refresh_expired,
            "expires_at": entry.expires_at.isoformat() if entry.expires_at else None,
        }

    # ── Creator info ──────────────────────────────────────────────────────────

    async def get_creator_info(self, access_token: str) -> dict:
        """Query TikTok creator info (privacy levels, max video duration, etc.)."""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(TIKTOK_CREATOR_INFO_URL, headers=headers)

        if res.status_code != 200:
            logger.error(f"TikTok creator_info failed: status={res.status_code}")
            return {"success": False, "error": f"HTTP {res.status_code}", "detail": res.text}

        data = res.json()
        if data.get("error", {}).get("code", "ok") != "ok":
            err = data["error"]
            logger.error(f"TikTok creator_info API error: {err.get('message')}")
            return {"success": False, "error": err.get("code"), "detail": err.get("message")}

        return {"success": True, "data": data.get("data", {})}

    # ── Video publishing ──────────────────────────────────────────────────────

    async def publish_video(
        self,
        access_token: str,
        video_url: str,
        title: str = "",
        privacy_level: str = "SELF_ONLY",
        disable_comment: bool = False,
        disable_duet: bool = False,
        disable_stitch: bool = False,
    ) -> dict:
        """
        Publish a video to TikTok using PULL_FROM_URL.

        Requires the `video.publish` scope to be granted AND the TikTok app
        to have passed the Content Posting API review. If not yet approved,
        TikTok will return error code `permission_denied` or similar.

        privacy_level options (from creator_info):
            PUBLIC_TO_EVERYONE | MUTUAL_FOLLOW_FRIENDS | FOLLOWER_OF_CREATOR | SELF_ONLY
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }
        body = {
            "post_info": {
                "title": title[:150],  # TikTok max title length
                "privacy_level": privacy_level,
                "disable_comment": disable_comment,
                "disable_duet": disable_duet,
                "disable_stitch": disable_stitch,
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "video_url": video_url,
            },
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(TIKTOK_VIDEO_INIT_URL, json=body, headers=headers)

        if res.status_code == 403:
            logger.error("TikTok publish 403 — video.publish scope not approved or app not audited")
            return {
                "success": False,
                "error": "permission_denied",
                "detail": (
                    "TikTok returned 403. The `video.publish` scope requires TikTok app review "
                    "approval. Your app may not yet have Content Posting API access. "
                    "Apply at: https://developers.tiktok.com/apps/"
                ),
            }

        if res.status_code != 200:
            logger.error(f"TikTok publish failed: status={res.status_code}")
            return {"success": False, "error": f"HTTP {res.status_code}", "detail": res.text}

        data = res.json()
        err = data.get("error", {})
        if err.get("code", "ok") != "ok":
            code = err.get("code", "")
            message = err.get("message", "Unknown TikTok error")
            logger.error(f"TikTok publish API error: code={code} message={message}")

            # Surface actionable messages
            if code in ("permission_denied", "scope_not_authorized"):
                detail = (
                    f"TikTok API error: {message}. "
                    "The `video.publish` scope requires TikTok Content Posting API approval. "
                    "Apply at https://developers.tiktok.com/apps/"
                )
            elif code == "access_token_invalid":
                detail = "TikTok access token is invalid or expired. Re-connect the account."
            elif code == "rate_limit_exceeded":
                detail = "TikTok rate limit exceeded. Please try again later."
            else:
                detail = message

            return {"success": False, "error": code, "detail": detail}

        return {"success": True, "data": data.get("data", {})}
