from app.db.session import SessionLocal

async def get_db():
    """
    Async database session dependency.
    Using async generator prevents FastAPI from spawning a new thread
    for each request (fixes RuntimeError: can't start new thread).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
