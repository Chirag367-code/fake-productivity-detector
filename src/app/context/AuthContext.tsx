/**
 * Authentication Context & Provider
 *
 * Wraps the app with Supabase auth state management.
 * Provides login, logout, session restoration, and user profile data.
 */

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import { supabase } from "../../lib/supabase";
import type { Session, User } from "@supabase/supabase-js";

// ── Types ──────────────────────────────────────────────────────────────────

export interface AppUser {
  id: string;
  email: string;
  name: string;
  photo: string;
  provider: string;
}

interface AuthContextValue {
  /** Currently authenticated user (null while loading or logged-out) */
  user: AppUser | null;
  /** Raw Supabase session */
  session: Session | null;
  /** True while the initial session is being restored */
  loading: boolean;
  /** Sign in with Google OAuth (redirects) */
  signInWithGoogle: () => Promise<void>;
  /** Sign in with email + password */
  signInWithEmail: (email: string, password: string) => Promise<{ error: string | null }>;
  /** Sign up with email + password */
  signUpWithEmail: (
    email: string,
    password: string,
    fullName: string
  ) => Promise<{ error: string | null; needsConfirmation: boolean }>;
  /** Resend sign-up confirmation email */
  resendConfirmationEmail: (email: string) => Promise<{ error: string | null }>;
  /** Sign out */
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

// ── Helpers ────────────────────────────────────────────────────────────────

function mapUser(user: User): AppUser {
  const meta = user.user_metadata ?? {};
  return {
    id: user.id,
    email: user.email ?? "",
    name:
      meta.full_name ??
      meta.name ??
      user.email?.split("@")[0] ??
      "User",
    photo:
      meta.avatar_url ??
      meta.picture ??
      `https://ui-avatars.com/api/?name=${encodeURIComponent(
        meta.full_name ?? meta.name ?? "U"
      )}&background=4F46E5&color=FFFFFF&size=100`,
    provider: user.app_metadata?.provider ?? "email",
  };
}

/**
 * Upserts the user row in the public.users table.
 * The DB trigger handles the insert on first sign-up, but we also
 * call this to keep name / avatar / provider up to date.
 */
async function upsertUserProfile(appUser: AppUser) {
  try {
    await supabase.from("users").upsert(
      {
        id: appUser.id,
        email: appUser.email,
        full_name: appUser.name,
        avatar_url: appUser.photo,
        provider: appUser.provider,
      },
      { onConflict: "id" }
    );
  } catch (err) {
    console.warn("Could not upsert user profile:", err);
  }
}

// ── Provider ───────────────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [user, setUser] = useState<AppUser | null>(null);
  const [loading, setLoading] = useState(true);

  // Restore session on mount & listen for auth changes
  useEffect(() => {
    // 1. Get existing session
    supabase.auth.getSession().then(({ data: { session: s } }) => {
      setSession(s);
      if (s?.user) {
        const mapped = mapUser(s.user);
        setUser(mapped);
        upsertUserProfile(mapped);
      }
      setLoading(false);
    });

    // 2. Listen for auth state changes (login, logout, token refresh)
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, s) => {
      setSession(s);
      if (s?.user) {
        const mapped = mapUser(s.user);
        setUser(mapped);
        upsertUserProfile(mapped);
      } else {
        setUser(null);
      }
      setLoading(false);
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  // ── Auth methods ───────────────────────────────────────────────────────

  const signInWithGoogle = useCallback(async () => {
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: window.location.origin,
      },
    });
  }, []);

  const signInWithEmail = useCallback(
    async (email: string, password: string) => {
      const { error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });
      const errMsg = error?.message ?? null;
      // Supabase rate-limit detection
      if (errMsg && /rate\s*limit|too many requests|429/i.test(errMsg)) {
        return { error: "Too many login attempts. Please wait at least 60 seconds before trying again." };
      }
      return { error: errMsg };
    },
    []
  );

  const signUpWithEmail = useCallback(
    async (email: string, password: string, fullName: string) => {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: { full_name: fullName },
        },
      });
      const errMsg = error?.message ?? null;
      if (errMsg && /rate\s*limit|too many requests|429/i.test(errMsg)) {
        return { error: "Too many sign-up attempts. Please wait at least 60 seconds before trying again.", needsConfirmation: false };
      }
      // needsConfirmation = sign-up succeeded but no session yet (email confirmation required)
      const needsConfirmation = !errMsg && !data.session;
      return { error: errMsg, needsConfirmation };
    },
    []
  );

  const resendConfirmationEmail = useCallback(async (email: string) => {
    const { error } = await supabase.auth.resend({ type: "signup", email });
    const errMsg = error?.message ?? null;
    if (errMsg && /rate\s*limit|too many requests|429/i.test(errMsg)) {
      return { error: "Too many resend requests. Please wait at least 60 seconds before trying again." };
    }
    return { error: errMsg };
  }, []);

  const signOut = useCallback(async () => {
    await supabase.auth.signOut();
    setUser(null);
    setSession(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        loading,
        signInWithGoogle,
        signInWithEmail,
        signUpWithEmail,
        resendConfirmationEmail,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// ── Hook ───────────────────────────────────────────────────────────────────

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return ctx;
}
