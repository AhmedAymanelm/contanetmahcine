import logging
import tweepy
import httpx
import tempfile
import os
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

    def publish_with_image(self, text: str, image_url: str) -> dict:
        """
        Downloads an image and publishes a tweet with media attachment.
        Falls back to text-only if image upload fails.
        """
        if not self._is_configured():
            return {"success": False, "message": "Twitter API keys missing"}

        tmp_path = None
        try:
            # Download the image
            resp = httpx.get(image_url, timeout=30.0, follow_redirects=True)
            if resp.status_code != 200:
                logger.warning(f"Could not download image for Twitter: {image_url} — falling back to text")
                return self.publish_text(text)

            suffix = ".jpg"
            content_type = resp.headers.get("content-type", "")
            if "png" in content_type:
                suffix = ".png"
            elif "gif" in content_type:
                suffix = ".gif"

            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                f.write(resp.content)
                tmp_path = f.name

            # Upload media via v1.1 API (required for media_upload)
            auth = tweepy.OAuth1UserHandler(
                self.api_key, self.api_secret,
                self.access_token, self.access_secret
            )
            api_v1 = tweepy.API(auth)
            media = api_v1.media_upload(filename=tmp_path)

            # Post tweet with media via v2 client
            client = tweepy.Client(
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_secret
            )
            response = client.create_tweet(text=text, media_ids=[media.media_id])
            logger.info(f"Posted to X with image. Tweet ID: {response.data['id']}")
            return {"success": True, "data": response.data}

        except Exception as e:
            logger.error(f"Failed to post to X with image: {e} — trying text only")
            return self.publish_text(text)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

    def publish_carousel(self, image_urls: list, text: str) -> dict:
        """
        Publishes up to 4 carousel images as a single tweet with multiple media attachments.
        Twitter API v2 supports max 4 images per tweet.
        Falls back to first image only if bulk upload fails.
        """
        if not self._is_configured():
            return {"success": False, "message": "Twitter API keys missing"}

        if not image_urls:
            return self.publish_text(text)

        auth = tweepy.OAuth1UserHandler(
            self.api_key, self.api_secret,
            self.access_token, self.access_secret
        )
        api_v1 = tweepy.API(auth)
        client = tweepy.Client(
            consumer_key=self.api_key,
            consumer_secret=self.api_secret,
            access_token=self.access_token,
            access_token_secret=self.access_secret
        )

        media_ids = []
        tmp_paths = []
        try:
            # Upload up to 4 images (Twitter limit)
            for img_url in image_urls[:4]:
                try:
                    resp = httpx.get(img_url, timeout=30.0, follow_redirects=True)
                    if resp.status_code != 200:
                        continue
                    suffix = ".png" if "png" in resp.headers.get("content-type", "") else ".jpg"
                    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                        f.write(resp.content)
                        tmp_paths.append(f.name)
                    media = api_v1.media_upload(filename=tmp_paths[-1])
                    media_ids.append(media.media_id)
                except Exception as e:
                    logger.warning(f"Failed to upload carousel image {img_url}: {e}")

            if not media_ids:
                return self.publish_text(text)

            response = client.create_tweet(text=text, media_ids=media_ids)
            logger.info(f"Posted carousel to X ({len(media_ids)} images). Tweet ID: {response.data['id']}")
            return {"success": True, "data": response.data}

        except Exception as e:
            logger.error(f"Failed to post carousel to X: {e} — trying first image only")
            if image_urls:
                return self.publish_with_image(text, image_urls[0])
            return self.publish_text(text)
        finally:
            for p in tmp_paths:
                if os.path.exists(p):
                    os.remove(p)

