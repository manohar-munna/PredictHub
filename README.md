# PredictHub 🎯

PredictHub is a skill-based prediction and event-trading platform where users bet virtual coins on future outcomes and win based on accuracy. Built using FastAPI, SQLAlchemy, and Jinja templates — optimized for deployment on Vercel.

🔗 Live Demo: https://predicthub-khaki.vercel.app

---

## ✨ Features

- User registration & secure login
- Virtual coins with live wallet balance
- Create and trade in YES/NO prediction markets
- Automatic reward distribution when events resolve
- Real-time odds & pool percentages displayed visually
- Leaderboard for top traders
- News page powered by NewsAPI to help prediction decisions
- Admin features:
  - Create markets
  - Resolve outcomes & payout winners
  - Search / edit / delete users

---

## 🛠️ Tech Stack

| Layer | Technology Used |
|------|----------------|
| Backend | FastAPI |
| Frontend Rendering | Jinja2 Templates (HTML / TailwindCSS styling) |
| Database | SQLAlchemy ORM with SQLite/PostgreSQL |
| Authentication | Session-based login |
| Security | bcrypt for password hashing |
| API Integration | NewsAPI.org |
| Deployment | Vercel (`vercel.json`) |

---

## 🗂️ Project Structure

