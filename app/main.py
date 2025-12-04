# app/main.py

from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from pathlib import Path
import bcrypt
from datetime import datetime
import requests
import time
import os 
from groq import Groq # <--- NEW IMPORT

from . import models, database

app = FastAPI(title="PredictHub")

# --- CONFIGURATION ---
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "") # <--- NEW KEY
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")

# --- AI CLIENT SETUP ---
client = None
if GROQ_API_KEY:
    try:
        client = Groq(api_key=GROQ_API_KEY)
    except:
        print("Groq Client failed to initialize")

# --- CACHING SETUP ---
NEWS_CACHE = {
    "data": {},
    "last_fetched": {} 
}
CACHE_TIMEOUT = 900 

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

# --- Helper: Check if Admin ---
def is_user_admin(user: models.User):
    return user and user.username == ADMIN_USERNAME

def calculate_percentages(market):
    total = market.yes_pool + market.no_pool
    if total == 0:
        return 50, 50
    yes_pct = round((market.yes_pool / total) * 100)
    no_pct = 100 - yes_pct 
    return yes_pct, no_pct

# --- NEW: AI ANALYSIS ROUTE ---
@app.post("/api/analyze/{market_id}")
async def analyze_market_ai(market_id: int, db: Session = Depends(get_db)):
    """
    Uses Groq Llama3 to analyze the market question.
    """
    if not client:
        return JSONResponse({"content": "⚠️ AI is currently offline (API Key missing)."})

    market = db.query(models.Market).filter(models.Market.id == market_id).first()
    if not market:
        return JSONResponse({"content": "Market not found."})

    # Prepare the prompt
    prompt = f"""
    You are a professional prediction market analyst (like on Polymarket).
    Market Question: "{market.question}"
    Description: "{market.description}"
    Category: {market.category}
    Current Pool: {market.yes_pool + market.no_pool} coins.
    
    Provide a concise, 2-3 sentence analysis of this event. 
    Focus on probabilities or key news factors to consider. 
    Do not be neutral—sound like a smart crypto trader.
    """

    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8192", 
        )
        return JSONResponse({"content": chat_completion.choices[0].message.content})
    except Exception as e:
        return JSONResponse({"content": "⚠️ AI Analysis failed. Try again later."})

# --- ROUTES ---

@app.get("/", response_class=HTMLResponse)
async def read_home(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    return templates.TemplateResponse("home.html", {
        "request": request, 
        "user": user,
        "is_admin": is_user_admin(user)
    })

@app.get("/news", response_class=HTMLResponse)
def read_news(request: Request, category: str = "general", refresh: bool = False, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    
    current_time = time.time()
    articles = []
    error = None

    if refresh and category in NEWS_CACHE["data"]:
        del NEWS_CACHE["data"][category]

    if category in NEWS_CACHE["data"] and (current_time - NEWS_CACHE["last_fetched"].get(category, 0) < CACHE_TIMEOUT):
        articles = NEWS_CACHE["data"][category]
    else:
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
            response = requests.get(url, timeout=5)
            data = response.json()
            if data.get("status") == "ok":
                articles = data.get("articles", [])[:20]
                NEWS_CACHE["data"][category] = articles
                NEWS_CACHE["last_fetched"][category] = current_time
            else:
                error = data.get("message", "Unable to fetch news.")
        except Exception as e:
            error = "Connection error to News API."

    return templates.TemplateResponse("news.html", {
        "request": request,
        "user": user,
        "articles": articles,
        "current_category": category,
        "error": error,
        "is_admin": is_user_admin(user)
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
        "transactions": transactions,
        "is_admin": is_user_admin(user)
    })

@app.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    top_users = db.query(models.User).order_by(models.User.balance.desc()).limit(10).all()
    
    return templates.TemplateResponse("leaderboard.html", {
        "request": request,
        "user": user,
        "top_users": top_users,
        "is_admin": is_user_admin(user)
    })

# --- MARKET ROUTES ---

@app.get("/markets", response_class=HTMLResponse)
async def read_markets(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    markets = db.query(models.Market).order_by(
        models.Market.is_open.desc(), 
        models.Market.id.desc()
    ).all()
    return templates.TemplateResponse("markets.html", {
        "request": request,
        "markets": markets,
        "user": user,
        "is_admin": is_user_admin(user)
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
    
    comments = db.query(models.Comment).filter(
        models.Comment.market_id == market_id
    ).order_by(models.Comment.timestamp.desc()).all()

    return templates.TemplateResponse("predict.html", {
        "request": request,
        "market": market,
        "previous_choice": previous_choice,
        "previous_wager": previous_wager,
        "yes_pct": yes_pct,
        "no_pct": no_pct,
        "user": user,
        "is_admin": is_user_admin(user),
        "comments": comments,
        # NEW: Pass pool data for JS Calculator
        "yes_pool": market.yes_pool,
        "no_pool": market.no_pool
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
    comments = db.query(models.Comment).filter(models.Comment.market_id == market_id).order_by(models.Comment.timestamp.desc()).all()
    
    return templates.TemplateResponse("predict.html", {
        "request": request,
        "market": market,
        "previous_choice": choice,
        "previous_wager": wager,
        "yes_pct": yes_pct,
        "no_pct": no_pct,
        "user": user,
        "message": f"Bet placed! {wager} coins deducted.",
        "is_admin": is_user_admin(user),
        "comments": comments,
        "yes_pool": market.yes_pool,
        "no_pool": market.no_pool
    })

@app.post("/predict/{market_id}/comment", response_class=RedirectResponse)
async def post_comment(
    market_id: int,
    content: str = Form(...),
    request: Request = None,
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    if content.strip():
        new_comment = models.Comment(content=content, user_id=user.id, market_id=market_id)
        db.add(new_comment)
        db.commit()
    return RedirectResponse(url=f"/predict/{market_id}", status_code=303)

# --- ADMIN ROUTES ---

@app.get("/admin/create", response_class=HTMLResponse)
async def create_market_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not is_user_admin(user):
         return HTMLResponse("Unauthorized Access", status_code=403)
         
    return templates.TemplateResponse("create_market.html", {"request": request, "user": user})

@app.post("/admin/create", response_class=RedirectResponse)
async def create_market_submit(
    request: Request,
    question: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not is_user_admin(user):
        return HTMLResponse("Unauthorized", status_code=403)

    new_market = models.Market(question=question, description=description, category=category, is_open=True)
    db.add(new_market)
    db.commit()
    return RedirectResponse(url="/markets", status_code=303)

@app.post("/admin/resolve/{market_id}", response_class=RedirectResponse)
async def resolve_market(
    request: Request,
    market_id: int,
    outcome: str = Form(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not is_user_admin(user):
        return HTMLResponse("Unauthorized", status_code=403)

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

@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users_dashboard(request: Request, search: str = None, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not is_user_admin(user):
         return HTMLResponse("Unauthorized Access", status_code=403)
    
    query = db.query(models.User)
    if search:
        query = query.filter(models.User.username.contains(search))
    all_users = query.order_by(models.User.id.asc()).all()
    
    return templates.TemplateResponse("admin_users.html", {
        "request": request, "user": user, "all_users": all_users,
        "is_admin": True, "search_query": search
    })

@app.post("/admin/users/update/{target_id}", response_class=RedirectResponse)
async def admin_update_balance(
    target_id: int, new_balance: int = Form(...), request: Request = None, db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not is_user_admin(user):
        return HTMLResponse("Unauthorized", status_code=403)

    target_user = db.query(models.User).filter(models.User.id == target_id).first()
    if target_user:
        diff = new_balance - target_user.balance
        target_user.balance = new_balance
        if diff != 0:
            txn = models.Transaction(user_id=target_user.id, amount=diff, description="Admin adjustment 🛠️")
            db.add(txn)
        db.commit()
    return RedirectResponse(url="/admin/users", status_code=303)

@app.post("/admin/users/delete/{target_id}", response_class=RedirectResponse)
async def admin_delete_user(target_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not is_user_admin(user):
        return HTMLResponse("Unauthorized", status_code=403)
    if user.id == target_id:
        return RedirectResponse(url="/admin/users", status_code=303)

    target_user = db.query(models.User).filter(models.User.id == target_id).first()
    if target_user:
        db.query(models.Vote).filter(models.Vote.user_id == target_id).delete()
        db.query(models.Transaction).filter(models.Transaction.user_id == target_id).delete()
        db.query(models.Comment).filter(models.Comment.user_id == target_id).delete()
        db.delete(target_user)
        db.commit()
    return RedirectResponse(url="/admin/users", status_code=303)