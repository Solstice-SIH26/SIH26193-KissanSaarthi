# Submission Guide

This document helps judges navigate this submission quickly.

## Where to find things

| What you're looking for   | Where to find it                                           |
| ------------------------- | ---------------------------------------------------------- |
| Project overview          | [README.md](./README.md)                                   |
| Live working demo         | See "Live Links" in README.md                              |
| Demo video                | [submission/DEMO.md](./submission/DEMO.md)                 |
| Presentation / pitch deck | [submission/PRESENTATION.md](./submission/PRESENTATION.md) |
| Screenshots               | [assets/screenshots/](./assets/screenshots/)               |
| System architecture       | [docs/architecture.md](./docs/architecture.md)             |
| API endpoints             | [docs/api.md](./docs/api.md)                               |
| Database schema           | [docs/database.md](./docs/database.md)                     |
| Frontend source code      | [frontend/](./frontend/)                                   |
| Backend source code       | [backend/](./backend/)                                     |

## How to run this project locally

### Backend

\`\`\`bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
\`\`\`
Visit `http://127.0.0.1:8000/docs` for the interactive API docs.

### Frontend

\`\`\`bash
cd frontend
npm install
npm run dev
\`\`\`

### Environment Variables

Both `frontend/.env.example` and `backend/.env.example` list the required
variables (Supabase URL/key, Twilio credentials, etc.) — copy each to
`.env` and fill in real values to run locally.

## What's built vs. planned

See the "Built" and "Planned" sections in
[submission/PRESENTATION.md](./submission/PRESENTATION.md) for an honest
breakdown of what's fully working today versus what's scoped for future
development (BHASHINI regional-language support, DTMF fallback, SMS
notifications).
