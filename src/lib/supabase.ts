/**
 * Supabase Client Configuration
 *
 * Initializes the Supabase client using environment variables.
 * Used for authentication and database operations.
 */

import { createClient } from "@supabase/supabase-js";

const supabaseUrl =
  import.meta.env.VITE_SUPABASE_URL ||
  "https://yimronvopzqhapclnbsv.supabase.co";
const supabaseAnonKey =
  import.meta.env.VITE_SUPABASE_ANON_KEY ||
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlpbXJvbnZvcHpxaGFwY2xuYnN2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQyNjYzMzUsImV4cCI6MjA5OTg0MjMzNX0.REviJYxxWqOESHcvepV4Z10yEkAl7UyvHS8oMS9-zJY";

if (!supabaseUrl || !supabaseAnonKey) {
  console.error(
    "Missing Supabase environment variables. " +
      "Please set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY."
  );
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
