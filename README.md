PredictHub 🎯

PredictHub is a skill-based prediction and event-trading platform where users bet virtual coins on future outcomes and win based on accuracy. Built using FastAPI, SQLAlchemy, and Jinja templates — optimized for deployment on Vercel.
Live Demo: https://predicthub-khaki.vercel.app

✨ Features

User registration & secure login

Virtual coins with wallet balance updates

Create and trade in YES/NO prediction markets

Automatic payout when events resolve

Leaderboard for top traders

News feed powered by NewsAPI for smarter decisions

Admin dashboard

Create Markets

Resolve outcomes

Edit/Delete users

🛠 Tech Stack

FastAPI (Backend)

Jinja2 Templates (Frontend Rendering)

SQLAlchemy ORM with SQLite/PostgreSQL

TailwindCSS Styled UI

Session-based Authentication

bcrypt Password Security

NewsAPI Integration

Deployed on Vercel

🗂 Project Structure

PredictHub/
├─ app/
│ ├─ main.py – FastAPI routes & admin logic
│ ├─ models.py – Database models (User, Market, Vote, Transaction)
│ ├─ database.py – DB configuration
│ ├─ templates/ – All UI pages
│ └─ static/ – Assets (if any)
├─ requirements.txt
├─ vercel.json
└─ README.md

🚀 Local Setup

1️⃣ Clone repo
git clone https://github.com/manohar-munna/PredictHub.git
cd PredictHub

2️⃣ Create venv & install deps
python -m venv venv
source venv/bin/activate (Windows: venv\Scripts\activate)
pip install -r requirements.txt

3️⃣ Set environment variables
export NEWS_API_KEY="your_api_key_here"
export ADMIN_USERNAME="admin"

4️⃣ Run server
uvicorn app.main:app --reload
Visit: http://localhost:8000/

🔐 Admin Access

The username set in ADMIN_USERNAME becomes admin.
Use it during registration to unlock admin controls.

🎯 Reward System

Users bet coins → pools increase

On resolve: winners receive payouts proportionally from the pool

🔥 Future Roadmap

Multi-option markets

Mobile UI improvements

Awards & streak bonuses

Live probability graphs

Real-money support (law compliant)

🤝 Contributing

Pull requests welcome.
If you like it — ⭐ star the repo!
