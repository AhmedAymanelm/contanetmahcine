from sqlalchemy import Column, Integer, String
from app.models.base import Base

class BannedWord(Base):
    __tablename__ = "banned_words"

    id = Column(Integer, primary_key=True, index=True)
    word = Column(String, unique=True, index=True, nullable=False)
    replacement = Column(String, nullable=True)
