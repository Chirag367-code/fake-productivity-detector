-- ============================================================================
-- Fake Productivity Detector - Supabase SQL Migration
-- ============================================================================
-- Run this SQL in the Supabase SQL Editor (Dashboard > SQL Editor > New Query)
-- This creates the required tables, RLS policies, and trigger functions.
-- ============================================================================

-- 1. USERS TABLE
-- Stores profile information synced from Supabase Auth.
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.users (
  id          UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email       TEXT UNIQUE NOT NULL,
  full_name   TEXT,
  avatar_url  TEXT,
  provider    TEXT DEFAULT 'email',
  created_at  TIMESTAMPTZ DEFAULT now()
);

-- Enable RLS
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- Users can read their own row
CREATE POLICY "Users can view own profile"
  ON public.users FOR SELECT
  USING (auth.uid() = id);

-- Users can update their own row
CREATE POLICY "Users can update own profile"
  ON public.users FOR UPDATE
  USING (auth.uid() = id);

-- Users can insert their own row (for upsert on first login)
CREATE POLICY "Users can insert own profile"
  ON public.users FOR INSERT
  WITH CHECK (auth.uid() = id);


-- 2. PRODUCTIVITY_RECORDS TABLE
-- Stores every productivity analysis linked to a user.
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.productivity_records (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  task_hours          FLOAT NOT NULL,
  idle_hours          FLOAT NOT NULL,
  social_media_usage  FLOAT NOT NULL,
  break_frequency     INTEGER NOT NULL,
  tasks_completed     INTEGER NOT NULL,
  score               INTEGER NOT NULL,
  category            TEXT NOT NULL,
  created_at          TIMESTAMPTZ DEFAULT now()
);

-- Enable RLS
ALTER TABLE public.productivity_records ENABLE ROW LEVEL SECURITY;

-- Users can read their own records
CREATE POLICY "Users can view own records"
  ON public.productivity_records FOR SELECT
  USING (auth.uid() = user_id);

-- Users can insert their own records
CREATE POLICY "Users can insert own records"
  ON public.productivity_records FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Users can delete their own records
CREATE POLICY "Users can delete own records"
  ON public.productivity_records FOR DELETE
  USING (auth.uid() = user_id);


-- 3. AUTO-CREATE USER ROW ON AUTH SIGN-UP
-- Trigger function that inserts a row into public.users when
-- a new user signs up via Supabase Auth (Google or email).
-- ============================================================================
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.users (id, email, full_name, avatar_url, provider)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.raw_user_meta_data->>'name', ''),
    COALESCE(NEW.raw_user_meta_data->>'avatar_url', NEW.raw_user_meta_data->>'picture', ''),
    COALESCE(NEW.raw_app_meta_data->>'provider', 'email')
  )
  ON CONFLICT (id) DO UPDATE SET
    full_name  = EXCLUDED.full_name,
    avatar_url = EXCLUDED.avatar_url,
    provider   = EXCLUDED.provider;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Drop existing trigger if exists, then create
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();


-- 4. INDEX for faster lookups
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_productivity_records_user_id
  ON public.productivity_records(user_id);

CREATE INDEX IF NOT EXISTS idx_productivity_records_created_at
  ON public.productivity_records(created_at DESC);


-- 5. PRODUCTIVITY_ANALYSIS TABLE (backend code table)
-- The backend's TableNames.PRODUCTIVITY_ANALYSIS points to this table.
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.productivity_analysis (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             TEXT NOT NULL,
  user_name           TEXT,
  task_hours          FLOAT NOT NULL DEFAULT 0,
  idle_hours          FLOAT NOT NULL DEFAULT 0,
  social_media_usage  FLOAT NOT NULL DEFAULT 0,
  break_frequency     INTEGER NOT NULL DEFAULT 0,
  tasks_completed     INTEGER NOT NULL DEFAULT 0,
  productivity_score  FLOAT NOT NULL DEFAULT 0,
  category_rule_based TEXT,
  category_ml         TEXT,
  suggestions         JSONB DEFAULT '[]'::jsonb,
  created_at          TIMESTAMPTZ DEFAULT now()
);

-- Enable RLS
ALTER TABLE public.productivity_analysis ENABLE ROW LEVEL SECURITY;

-- Users can view their own analysis records
CREATE POLICY "Users can view own productivity_analysis"
  ON public.productivity_analysis FOR SELECT
  USING (auth.uid()::text = user_id);

-- Users can insert their own analysis records
CREATE POLICY "Users can insert own productivity_analysis"
  ON public.productivity_analysis FOR INSERT
  WITH CHECK (auth.uid()::text = user_id);

-- Users can delete their own analysis records
CREATE POLICY "Users can delete own productivity_analysis"
  ON public.productivity_analysis FOR DELETE
  USING (auth.uid()::text = user_id);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_productivity_analysis_user_id
  ON public.productivity_analysis(user_id);


-- ============================================================================
-- 6. AGENT AUTHENTICITY RECORDS TABLE
-- Stores daily aggregated authenticity scores from the local behavioral agent.
-- Added as part of the Local Behavioral Agent feature extension.
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.agent_authenticity_records (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  date                DATE NOT NULL,
  authenticity_score  FLOAT NOT NULL CHECK (authenticity_score >= 0 AND authenticity_score <= 100),
  avg_typing_speed    FLOAT,
  avg_mouse_velocity  FLOAT,
  top_window_categories JSONB DEFAULT '[]'::jsonb,
  created_at          TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, date)
);

-- Enable RLS
ALTER TABLE public.agent_authenticity_records ENABLE ROW LEVEL SECURITY;

-- Users can read their own agent records
CREATE POLICY "Users can view own agent records"
  ON public.agent_authenticity_records FOR SELECT
  USING (auth.uid() = user_id);

-- Users can insert their own agent records
CREATE POLICY "Users can insert own agent records"
  ON public.agent_authenticity_records FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Users can update their own agent records (for re-sync on same day)
CREATE POLICY "Users can update own agent records"
  ON public.agent_authenticity_records FOR UPDATE
  USING (auth.uid() = user_id);

-- Users can delete their own agent records
CREATE POLICY "Users can delete own agent records"
  ON public.agent_authenticity_records FOR DELETE
  USING (auth.uid() = user_id);

-- Index for fast lookups by user and date
CREATE INDEX IF NOT EXISTS idx_agent_authenticity_user_date
  ON public.agent_authenticity_records(user_id, date DESC);