# app/models.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    balance = Column(Integer, default=1000)
    
    votes = relationship("Vote", back_populates="user")
    # NEW: Link to history
    transactions = relationship("Transaction", back_populates="user")

class Market(Base):
    __tablename__ = "markets"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(String, index=True)
    category = Column(String)
    
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
    choice = Column(String)
    wager = Column(Integer, default=0)
    
    user = relationship("User", back_populates="votes")
    market = relationship("Market", back_populates="votes")

# NEW TABLE
class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Integer) # Can be positive (win) or negative (bet)
    description = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="transactions")
