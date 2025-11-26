# app/models.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    
    # NEW: Wallet Balance (Starts at 1000)
    balance = Column(Integer, default=1000)
    
    votes = relationship("Vote", back_populates="user")

class Market(Base):
    __tablename__ = "markets"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(String, index=True)
    category = Column(String)
    
    # NEW: Track amount of MONEY bet, not just number of votes
    yes_pool = Column(Integer, default=0)
    no_pool = Column(Integer, default=0)
    
    is_open = Column(Boolean, default=True)
    result = Column(String, nullable=True)
    
    votes = relationship("Vote", back_populates="market")

class Vote(Base):
    __tablename__ = "votes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    market_id = Column(Integer, ForeignKey("markets.id"))
    choice = Column(String) # 'yes' or 'no'
    
    # NEW: How much did they bet?
    wager = Column(Integer, default=0)
    
    user = relationship("User", back_populates="votes")
    market = relationship("Market", back_populates="votes")