import logging
import tweepy
from app.core.config import settings

logger = logging.getLogger(__name__)

class TwitterService:
    def __init__(self):
        self.api_key = settings.TWITTER_API_KEY
        self.api_secret = settings.TWITTER_API_SECRET
        self.access_token = settings.TWITTER_ACCESS_TOKEN
        self.access_secret = settings.TWITTER_ACCESS_SECRET

    def _is_configured(self) -> bool:
        return bool(
            self.api_key and 
            self.api_secret and 
            self.access_token and 
            self.access_secret
        )

    def publish_text(self, text: str) -> dict:
        """
        Publishes a tweet using the X (Twitter) API v2.
        """
        if not self._is_configured():
            logger.error("Twitter (X) API is not fully configured.")
            return {"success": False, "message": "Twitter API keys missing"}
            
        try:
            # We use tweepy Client for Twitter API v2
            client = tweepy.Client(
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_secret
            )
            
            # Post the tweet
            response = client.create_tweet(text=text)
            
            logger.info(f"Successfully posted to X. Tweet ID: {response.data['id']}")
            return {"success": True, "data": response.data}
            
        except tweepy.errors.TweepyException as e:
            logger.error(f"Failed to post to X: {e}")
            return {"success": False, "message": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error posting to X: {e}")
            return {"success": False, "message": str(e)}
