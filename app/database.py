# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Get DB URL
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# DIAGNOSTIC PRINT: This will show up in Vercel Logs!
if not SQLALCHEMY_DATABASE_URL:
    print("⚠️ WARNING: DATABASE_URL not found. Falling back to SQLite.")
    SQLALCHEMY_DATABASE_URL = "sqlite:///./predict.db"
else:
    print("✅ SUCCESS: Found DATABASE_URL environment variable.")

# Fix for Neon/Postgres URL format
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Args for SQLite only
connect_args = {}
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    connect_args = {"check_same_thread": False}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args=connect_args
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
