# AFP Paint Suggestion App

Implementation of `AFP_Rebuild_Guide_NextJS_FastAPI_Supabase.md`.

- `backend`: FastAPI workflow API with Supabase-compatible table calls and an in-memory mock mode.
- `frontend`: Next.js, TypeScript, Tailwind dashboard for import, BOM generation, suggestions, approvals, and exports.
- `supabase`: schema and seed SQL.
- `samples`: sample Revit paint JSON.

## Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

By default `AFP_USE_MOCK_DB=true`, so local testing works without Supabase credentials.

## Frontend

```bash
cd frontend
npm.cmd install
copy .env.local.example .env.local
npm.cmd run dev
```

Open `http://localhost:3000`.

## Supabase

Run `supabase/schema.sql`, then `supabase/seed.sql`. Set backend `.env` with `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and `AFP_USE_MOCK_DB=false`.
