# app/main.py

from dotenv import load_dotenv
import os

load_dotenv()

from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from pathlib import Path
import bcrypt
from datetime import datetime
import requests
import time # <--- Needed for caching

from . import models, database

app = FastAPI(title="PredictHub")

# --- CONFIGURATION ---

# 🔴 PASTE YOUR NEWSAPI.ORG KEY HERE 🔴
NEWS_API_KEY = os.getenv("NewsAPI_key")

# --- CACHING SETUP (NEW) ---
# We store news here so we don't have to call the API every second
NEWS_CACHE = {
    "data": {},       # Stores the articles: {'sports': [...], 'bollywood': [...]}
    "last_fetched": {} # Stores the time: {'sports': 17000000.00}
}
CACHE_TIMEOUT = 900 # 15 Minutes (in seconds)

# --- Security Setup ---

def get_password_hash(password):
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password, hashed_password):
    pwd_bytes = plain_password.encode('utf-8')
    hash_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(pwd_bytes, hash_bytes)

# --- Database Setup ---
models.Base.metadata.create_all(bind=database.engine)

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Config & Paths ---
BASE_DIR = Path(__file__).resolve().parent
app.add_middleware(SessionMiddleware, secret_key="super-secret-temporary-key")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# --- Helper: Get Current User ---
def get_current_user(request: Request, db: Session):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.query(models.User).filter(models.User.id == user_id).first()

def calculate_percentages(market):
    total = market.yes_pool + market.no_pool
    if total == 0:
        return 50, 50
    yes_pct = round((market.yes_pool / total) * 100)
    no_pct = 100 - yes_pct 
    return yes_pct, no_pct

# --- Startup Seed ---
@app.on_event("startup")
def startup_populate_db():
    db = database.SessionLocal()
    if db.query(models.Market).count() == 0:
        samples = [
            models.Market(question="Will it rain in Mumbai tomorrow?", category="Weather"),
            models.Market(question="Will India win the next cricket ODI match?", category="Sports"),
            models.Market(question="Bitcoin price above $100k by Dec 31?", category="Crypto"),
        ]
        db.add_all(samples)
        db.commit()
    db.close()

# --- ROUTES ---

@app.get("/", response_class=HTMLResponse)
async def read_home(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    return templates.TemplateResponse("home.html", {"request": request, "user": user})

# --- NEWS ROUTE (OPTIMIZED WITH CACHE) ---
# Note: Removed 'async' to allow threading for requests (prevents server freezing)
@app.get("/news", response_class=HTMLResponse)
def read_news(request: Request, category: str = "general", db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    
    current_time = time.time()
    articles = []
    error = None

    # 1. CHECK CACHE FIRST
    # If we have data AND it is less than 15 minutes old
    if category in NEWS_CACHE["data"] and (current_time - NEWS_CACHE["last_fetched"].get(category, 0) < CACHE_TIMEOUT):
        print(f"⚡ Serving {category} news from CACHE (Instant)")
        articles = NEWS_CACHE["data"][category]
    
    else:
        # 2. FETCH FROM API (If cache is empty or old)
        print(f"🌍 Fetching {category} news from API (Slow)...")
        
        search_terms = {
            "general": "india news",
            "business": "india business market stocks",
            "technology": "india technology startup crypto",
            "sports": "india cricket sports",
            "bollywood": "bollywood movies",
            "politics": "india politics government"
        }
        query = search_terms.get(category, "india")
        url = f"https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&apiKey={NEWS_API_KEY}"

        try:
            response = requests.get(url, timeout=5) # Add timeout so it doesn't hang forever
            data = response.json()
            
            if data.get("status") == "ok":
                articles = data.get("articles", [])[:20]
                # SAVE TO CACHE
                NEWS_CACHE["data"][category] = articles
                NEWS_CACHE["last_fetched"][category] = current_time
            else:
                error = data.get("message", "Unable to fetch news.")
                
        except Exception as e:
            print(f"Error: {e}")
            error = "Connection error to News API."

    return templates.TemplateResponse("news.html", {
        "request": request,
        "user": user,
        "articles": articles,
        "current_category": category,
        "error": error
    })


# --- AUTH ROUTES ---

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register", response_class=RedirectResponse)
async def register_submit(
    request: Request, 
    username: str = Form(...), 
    password: str = Form(...), 
    db: Session = Depends(get_db)
):
    existing_user = db.query(models.User).filter(models.User.username == username).first()
    if existing_user:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Username taken"})
    
    hashed_pw = get_password_hash(password)
    new_user = models.User(username=username, hashed_password=hashed_pw, balance=1000)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    txn = models.Transaction(user_id=new_user.id, amount=1000, description="Welcome Bonus 🎁")
    db.add(txn)
    db.commit()
    
    return RedirectResponse(url="/login", status_code=303)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login", response_class=RedirectResponse)
async def login_submit(
    request: Request, 
    username: str = Form(...), 
    password: str = Form(...), 
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})
    
    request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=303)

@app.get("/logout", response_class=RedirectResponse)
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)

@app.get("/profile", response_class=HTMLResponse)
async def read_profile(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    user_votes = db.query(models.Vote).filter(models.Vote.user_id == user.id).all()
    transactions = db.query(models.Transaction).filter(
        models.Transaction.user_id == user.id
    ).order_by(models.Transaction.timestamp.desc()).all()
    
    return templates.TemplateResponse("profile.html", {
        "request": request, 
        "user": user, 
        "votes": user_votes,
        "transactions": transactions
    })

@app.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    top_users = db.query(models.User).order_by(models.User.balance.desc()).limit(10).all()
    
    return templates.TemplateResponse("leaderboard.html", {
        "request": request,
        "user": user,
        "top_users": top_users
    })

# --- MARKET ROUTES ---

@app.get("/markets", response_class=HTMLResponse)
async def read_markets(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    markets = db.query(models.Market).order_by(models.Market.id.desc()).all()
    return templates.TemplateResponse("markets.html", {
        "request": request,
        "markets": markets,
        "user": user
    })

@app.get("/predict/{market_id}", response_class=HTMLResponse)
async def read_predict(request: Request, market_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    market = db.query(models.Market).filter(models.Market.id == market_id).first()
    if not market:
        return HTMLResponse("Market not found", status_code=404)

    previous_choice = None
    previous_wager = 0
    if user:
        existing_vote = db.query(models.Vote).filter(
            models.Vote.user_id == user.id, 
            models.Vote.market_id == market_id
        ).first()
        if existing_vote:
            previous_choice = existing_vote.choice
            previous_wager = existing_vote.wager
    
    yes_pct, no_pct = calculate_percentages(market)

    return templates.TemplateResponse("predict.html", {
        "request": request,
        "market": market,
        "previous_choice": previous_choice,
        "previous_wager": previous_wager,
        "yes_pct": yes_pct,
        "no_pct": no_pct,
        "user": user
    })

@app.post("/predict/{market_id}", response_class=HTMLResponse)
async def submit_prediction(
    request: Request, 
    market_id: int, 
    choice: str = Form(...),
    wager: int = Form(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    market = db.query(models.Market).filter(models.Market.id == market_id).first()
    
    if not market.is_open:
        return HTMLResponse("Error: This market is closed.", status_code=400)
    
    if not user:
         return RedirectResponse(url="/login", status_code=303)

    if wager <= 0:
        return HTMLResponse("Error: Wager must be positive.", status_code=400)
    if wager > user.balance:
        return HTMLResponse("Error: Insufficient funds!", status_code=400)

    existing_vote = db.query(models.Vote).filter(
        models.Vote.user_id == user.id, 
        models.Vote.market_id == market_id
    ).first()

    if existing_vote:
        return HTMLResponse("Error: You have already bet on this market.", status_code=400)

    user.balance -= wager
    new_vote = models.Vote(user_id=user.id, market_id=market_id, choice=choice, wager=wager)
    db.add(new_vote)
    
    txn = models.Transaction(
        user_id=user.id, 
        amount=-wager, 
        description=f"Bet on {market.question} ({choice.upper()})"
    )
    db.add(txn)
    
    if choice == "yes": market.yes_pool += wager
    else: market.no_pool += wager

    db.commit()
    db.refresh(market)
    
    yes_pct, no_pct = calculate_percentages(market)
    
    return templates.TemplateResponse("predict.html", {
        "request": request,
        "market": market,
        "previous_choice": choice,
        "previous_wager": wager,
        "yes_pct": yes_pct,
        "no_pct": no_pct,
        "user": user,
        "message": f"Bet placed! {wager} coins deducted."
    })

# --- ADMIN ROUTES ---

@app.get("/admin/create", response_class=HTMLResponse)
async def create_market_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
         return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("create_market.html", {"request": request, "user": user})

@app.post("/admin/create", response_class=RedirectResponse)
async def create_market_submit(
    request: Request,
    question: str = Form(...),
    category: str = Form(...),
    db: Session = Depends(get_db)
):
    new_market = models.Market(question=question, category=category, is_open=True)
    db.add(new_market)
    db.commit()
    return RedirectResponse(url="/markets", status_code=303)

@app.post("/admin/resolve/{market_id}", response_class=RedirectResponse)
async def resolve_market(
    market_id: int,
    outcome: str = Form(...),
    db: Session = Depends(get_db)
):
    market = db.query(models.Market).filter(models.Market.id == market_id).first()
    if market and market.is_open:
        market.is_open = False
        market.result = outcome
        
        total_pool = market.yes_pool + market.no_pool
        winning_pool = market.yes_pool if outcome == 'yes' else market.no_pool
        
        if winning_pool > 0:
            votes = db.query(models.Vote).filter(models.Vote.market_id == market_id).all()
            for vote in votes:
                if vote.choice == outcome:
                    share = vote.wager / winning_pool
                    payout = int(share * total_pool)
                    vote.user.balance += payout
                    txn = models.Transaction(
                        user_id=vote.user.id, 
                        amount=payout, 
                        description=f"Won bet on {market.question}!"
                    )
                    db.add(txn)
        db.commit()
        
    return RedirectResponse(url=f"/predict/{market_id}", status_code=303)
