import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

target_url = os.getenv("DATABASE_URL")
conn = psycopg2.connect(target_url)
cur = conn.cursor()

tokens = [
    ("facebook", os.getenv("FACEBOOK_ACCESS_TOKEN"), os.getenv("FACEBOOK_PAGE_ID")),
    ("instagram", os.getenv("INSTAGRAM_ACCESS_TOKEN"), os.getenv("INSTAGRAM_ACCOUNT_ID")),
    ("twitter", os.getenv("TWITTER_ACCESS_TOKEN"), "1802382735429750784") # Derived from token prefix
]

for platform, token, acc_id in tokens:
    if token:
        try:
            cur.execute("""
                INSERT INTO oauth_tokens (platform, access_token, account_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (platform) DO UPDATE 
                SET access_token = EXCLUDED.access_token,
                    account_id = EXCLUDED.account_id
            """, (platform, token, acc_id))
            print(f"Inserted {platform} into DB.")
        except Exception as e:
            print(f"Failed to insert {platform}: {e}")
            conn.rollback()

conn.commit()
cur.close()
conn.close()
print("Done.")
