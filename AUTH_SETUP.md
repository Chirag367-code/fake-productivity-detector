# Authentication Setup Guide

This document explains how to set up **Supabase authentication** for the Fake Productivity Detector project.

---

## 1. Create a Supabase Project

1. Go to [https://supabase.com](https://supabase.com) and create a free account.
2. Click **New Project**, choose an organization, enter a project name, set a database password, and select a region.
3. Wait for the project to finish provisioning.

---

## 2. Get Your Credentials

In the Supabase Dashboard go to **Settings → API**:

| Variable | Where to find it |
|---|---|
| `SUPABASE_URL` / `VITE_SUPABASE_URL` | Project URL (e.g. `https://abcdefg.supabase.co`) |
| `SUPABASE_KEY` / `VITE_SUPABASE_ANON_KEY` | `anon` / `public` key |
| `SUPABASE_JWT_SECRET` (optional, backend) | JWT Secret (scroll down) |

---

## 3. Run the Database Migration

1. In the Supabase Dashboard go to **SQL Editor → New Query**.
2. Paste the contents of [`supabase/migration.sql`](supabase/migration.sql).
3. Click **Run** to create the `users` and `productivity_records` tables, RLS policies, and the auto-create-user trigger.

---

## 4. Enable Google OAuth

1. In the Supabase Dashboard go to **Authentication → Providers → Google**.
2. Toggle **Enable**.
3. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials) and create an **OAuth 2.0 Client ID**:
   - Authorized JavaScript Origins: `http://localhost:5173` (and your production URL)
   - Authorized Redirect URIs: `https://<your-project-id>.supabase.co/auth/v1/callback`
4. Copy the **Client ID** and **Client Secret** back into the Supabase Google provider settings.
5. Click **Save**.

---

## 5. Configure Environment Variables

### Frontend (project root)

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env`:

```env
VITE_API_URL=http://localhost:8000
VITE_SUPABASE_URL=https://your-project-id.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-public-key
```

### Backend (`backend/`)

Copy `backend/.env.example` to `backend/.env`:

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env`:

```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-anon-public-key
# Optional – enables JWT verification on backend:
SUPABASE_JWT_SECRET=your-jwt-secret
```

---

## 6. Running on Another Computer

When cloning the project on a new machine:

```bash
git clone <repo-url>
cd <project>
cp .env.example .env          # fill in your Supabase credentials
cp backend/.env.example backend/.env   # fill in your Supabase credentials
npm install                    # frontend dependencies
cd backend && pip install -r requirements.txt   # backend dependencies
```

Then start both servers:

```bash
# Terminal 1 – Backend
cd backend
uvicorn app.main:app --reload

# Terminal 2 – Frontend
npm run dev
```

---

## 7. Password Rules (Email Sign-Up)

When signing up with email/password the password must satisfy:

- Minimum **4 characters**
- At least **2 numbers**
- At least **1 special character** (e.g. `!@#$%^&*`)

Examples of valid passwords: `ab12!`, `test34@`, `xy99#`

---

## 8. How Authentication Works

### Frontend Flow

1. User clicks **Sign in with Google** or fills the email/password form.
2. Supabase handles OAuth redirect or email/password sign-in.
3. On success, the `AuthProvider` stores the session and maps the Supabase `User` object to an `AppUser`.
4. The user row is upserted into `public.users` via the Supabase client.
5. All subsequent API calls include the `Authorization: Bearer <access_token>` header automatically via the `authFetch` helper.
6. Sessions are automatically restored on page refresh via `supabase.auth.getSession()`.

### Backend Flow

1. The backend receives the `Authorization` header.
2. If `SUPABASE_JWT_SECRET` is configured, the JWT is verified and the `sub` claim (user UUID) is extracted.
3. If the secret is not configured, the backend falls back to `"anonymous"` (development mode).

### Row Level Security

- The `users` table allows each user to read, insert, and update only their own row.
- The `productivity_records` table allows each user to read, insert, and delete only their own records.
- The database trigger `on_auth_user_created` automatically creates a `users` row when a new Supabase Auth user signs up.
