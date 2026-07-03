# Multi-Currency Wallet Platform

A full-stack wallet platform supporting account creation, multi-currency wallet
management, currency conversion, user-to-user transfers, and transaction history.

🚧 **Status:** Initial scaffold. Project structure is being set up. This README
will be updated as features land — see the checklist below for current progress.

## Tech Stack

- **Backend:** Python, FastAPI
- **Frontend:** Vue 3
- **Database:** PostgreSQL (planned)
- **Cache/Queue:** Redis (planned, for exchange rate caching)
- **Containerization:** Docker, docker-compose
- **CI/CD:** GitHub Actions (planned)

## Structure

- `server/` — FastAPI backend
- `app/` — Vue 3 frontend

## Server

```bash
cd server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

## App

```bash
cd app
npm install
npm run dev
```

## Roadmap

- [x] Project scaffold (server + app)
- [ ] Account creation & authentication
- [ ] Multi-currency wallet management
- [ ] Currency conversion
- [ ] User-to-user transfers
- [ ] Transaction history
- [ ] Dockerize (server, app, db, redis)
- [ ] CI/CD pipeline
