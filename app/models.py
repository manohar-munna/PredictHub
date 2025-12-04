# app/models.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text
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
    transactions = relationship("Transaction", back_populates="user")
    comments = relationship("Comment", back_populates="user")

class Market(Base):
    __tablename__ = "markets"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(String, index=True)
    description = Column(Text, nullable=True) # <--- NEW: Details about the market
    category = Column(String)
    
    yes_pool = Column(Integer, default=0)
    no_pool = Column(Integer, default=0)
    
    is_open = Column(Boolean, default=True)
    result = Column(String, nullable=True)
    
    votes = relationship("Vote", back_populates="market")
    comments = relationship("Comment", back_populates="market")

class Vote(Base):
    __tablename__ = "votes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    market_id = Column(Integer, ForeignKey("markets.id"))
    choice = Column(String)
    wager = Column(Integer, default=0)
    
    user = relationship("User", back_populates="votes")
    market = relationship("Market", back_populates="votes")

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Integer)
    description = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="transactions")

# NEW: Comments Table
class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    user_id = Column(Integer, ForeignKey("users.id"))
    market_id = Column(Integer, ForeignKey("markets.id"))
    
    user = relationship("User", back_populates="comments")
    market = relationship("Market", back_populates="comments")