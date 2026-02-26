# Examora Teacher UI (Shadcn Style)

## Run locally

1. Install dependencies:
   - `cd frontend-shadcn`
   - `npm install`
2. Dev server:
   - `npm run dev`
3. Production build (served by FastAPI at `/teacher`):
   - `npm run build`

## Backend integration

- UI calls these backend endpoints:
  - `GET /subjects`
  - `GET /chapters/{subject}`
  - `POST /generate-paper`

After build, FastAPI serves `frontend-shadcn/dist/index.html` from `/teacher`.
If `dist` does not exist, it falls back to the legacy `frontend/index.html`.
