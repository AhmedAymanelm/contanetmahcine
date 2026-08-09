from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.services.social.threads_service import ThreadsService

router = APIRouter()
threads_service = ThreadsService()

@router.get("/status")
def get_threads_status(db: Session = Depends(get_db)):
    """Returns the current connection status of Threads."""
    return threads_service.get_status(db)

@router.get("/me")
async def get_threads_me(db: Session = Depends(get_db)):
    """Fetches the connected Threads user profile."""
    access_token = await threads_service.check_and_refresh_token(db)
    if not access_token:
        raise HTTPException(status_code=401, detail="Threads account not connected or token expired.")
    
    res = await threads_service.get_user_profile(access_token)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res["error"])
    
    return res["data"]

@router.post("/publish")
async def publish_to_threads(
    text: str = Body(..., embed=True),
    media_url: str = Body(None, embed=True), # Optional image/video support (currently text only implementation)
    db: Session = Depends(get_db)
):
    """Publishes a text post to Threads."""
    access_token = await threads_service.check_and_refresh_token(db)
    if not access_token:
        raise HTTPException(status_code=401, detail="Threads account not connected or token expired.")
    
    status = threads_service.get_status(db)
    user_id = status.get("account_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Threads user ID not found.")

    res = await threads_service.publish_text(text, access_token, user_id)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res["error"])
    
    return {"status": "success", "data": res["data"]}
