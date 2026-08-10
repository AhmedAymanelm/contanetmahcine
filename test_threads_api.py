import sys, os
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from app.db.session import SessionLocal
from app.models.oauth_token import OAuthToken
import httpx

db = SessionLocal()
token = db.query(OAuthToken).filter(OAuthToken.platform == 'threads').first()

if token:
    print("Found Threads Token:", token.access_token[:10])
    url = f"https://graph.threads.net/v1.0/me/threads?fields=id,like_count,reply_count&access_token={token.access_token}"
    res = httpx.get(url)
    print(res.status_code)
    print(res.json())
else:
    print("No threads token found")
