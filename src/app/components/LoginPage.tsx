import { motion, AnimatePresence } from "motion/react";
import { Activity, Chrome, Mail, Lock, User, AlertCircle, Loader2, CheckCircle, RefreshCw } from "lucide-react";
import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import { validatePassword } from "../../lib/validation";

type AuthTab = "login" | "signup";
type View = "auth" | "confirm-pending";

const PENDING_EMAIL_KEY = "fpd_pending_confirm_email";

export function LoginPage() {
  const { signInWithGoogle, signInWithEmail, signUpWithEmail, resendConfirmationEmail } = useAuth();

  const [view, setView] = useState<View>(() =>
    localStorage.getItem(PENDING_EMAIL_KEY) ? "confirm-pending" : "auth"
  );
  const [tab, setTab] = useState<AuthTab>("login");
  const [email, setEmail] = useState(() => localStorage.getItem(PENDING_EMAIL_KEY) ?? "");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [passwordErrors, setPasswordErrors] = useState<string[]>([]);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [globalCooldown, setGlobalCooldown] = useState(0);

  // Countdown for resend cooldown
  useEffect(() => {
    if (resendCooldown <= 0) return;
    const t = setTimeout(() => setResendCooldown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [resendCooldown]);

  // Countdown for global rate-limit cooldown (blocks all auth actions)
  useEffect(() => {
    if (globalCooldown <= 0) return;
    const t = setTimeout(() => setGlobalCooldown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [globalCooldown]);

  const enterConfirmPending = (pendingEmail: string) => {
    localStorage.setItem(PENDING_EMAIL_KEY, pendingEmail);
    setEmail(pendingEmail);
    setView("confirm-pending");
    setError(null);
    setInfo(null);
  };

  const exitConfirmPending = () => {
    localStorage.removeItem(PENDING_EMAIL_KEY);
    setView("auth");
    setTab("login");
    setError(null);
    setInfo(null);
  };

  // ── Password live-validation ───────────────────────────────────────────
  const handlePasswordChange = (value: string) => {
    setPassword(value);
    if (tab === "signup" && value.length > 0) {
      const { errors } = validatePassword(value);
      setPasswordErrors(errors);
    } else {
      setPasswordErrors([]);
    }
  };

  // ── Google OAuth ───────────────────────────────────────────────────────
  const handleGoogleLogin = async () => {
    setError(null);
    setLoading(true);
    try {
      await signInWithGoogle();
    } catch {
      setError("Google sign-in failed. Please try again.");
      setLoading(false);
    }
  };

  // ── Resend Confirmation ────────────────────────────────────────────────
  const handleResendConfirmation = async () => {
    const target = email || (localStorage.getItem(PENDING_EMAIL_KEY) ?? "");
    if (!target) return;
    setLoading(true);
    setError(null);
    setInfo(null);
    const { error: resendError } = await resendConfirmationEmail(target);
    if (resendError) {
      setError(resendError);
      // If rate-limited, set a global cooldown so all buttons are blocked
      if (/rate\s*limit|too many|wait|60 second/i.test(resendError)) {
        setGlobalCooldown(60);
      }
    } else {
      setInfo("Confirmation email resent! Check your inbox (and spam folder).");
      setResendCooldown(60);
    }
    setLoading(false);
  };

  // ── Email Sign In ─────────────────────────────────────────────────────
  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setInfo(null);

    if (!email || !password) return;

    setLoading(true);
    const { error: authError } = await signInWithEmail(email, password);
    if (authError) {
      if (/rate\s*limit|too many|wait|60 second/i.test(authError)) {
        setError(authError);
        setGlobalCooldown(60);
      } else if (
        authError.toLowerCase().includes("email not confirmed") ||
        authError.toLowerCase().includes("not confirmed")
      ) {
        // Auto-redirect to the confirmation-pending screen
        enterConfirmPending(email);
      } else {
        setError(authError);
      }
    } else {
      // Successful sign-in — clear any stale pending state
      localStorage.removeItem(PENDING_EMAIL_KEY);
    }
    setLoading(false);
  };

  // ── Email Sign Up ─────────────────────────────────────────────────────
  const handleEmailSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setInfo(null);

    const { valid, errors } = validatePassword(password);
    if (!valid) {
      setPasswordErrors(errors);
      setError("Please fix the password errors below.");
      return;
    }

    if (!email || !fullName) return;

    setLoading(true);
    const { error: authError, needsConfirmation } = await signUpWithEmail(email, password, fullName);
    if (authError) {
      if (/rate\s*limit|too many|wait|60 second/i.test(authError)) {
        setError(authError);
        setGlobalCooldown(60);
      } else if (authError.toLowerCase().includes("already registered") || authError.toLowerCase().includes("already exists")) {
        // "User already registered" — just send them to sign in
        setTab("login");
        setError("An account with this email already exists. Please sign in.");
      } else {
        setError(authError);
      }
    } else if (needsConfirmation) {
      // Email confirmation required — show dedicated confirmation screen
      enterConfirmPending(email);
    }
    // If !needsConfirmation → Supabase auto-signed in; onAuthStateChange handles routing
    setLoading(false);
  };

  // ── Shared background & card wrapper ─────────────────────────────────
  const bg = (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      <div className="absolute top-20 left-20 w-72 h-72 bg-blue-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob" />
      <div className="absolute top-40 right-20 w-72 h-72 bg-purple-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-2000" />
      <div className="absolute bottom-20 left-1/2 w-72 h-72 bg-pink-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-4000" />
    </div>
  );

  const blobStyles = `
    @keyframes blob {
      0%, 100% { transform: translate(0px, 0px) scale(1); }
      33% { transform: translate(30px, -50px) scale(1.1); }
      66% { transform: translate(-20px, 20px) scale(0.9); }
    }
    .animate-blob { animation: blob 7s infinite; }
    .animation-delay-2000 { animation-delay: 2s; }
    .animation-delay-4000 { animation-delay: 4s; }
  `;

  // ── Confirmation-pending screen ───────────────────────────────────────
  if (view === "confirm-pending") {
    const pendingEmail = email || (localStorage.getItem(PENDING_EMAIL_KEY) ?? "");
    return (
      <div className="min-h-screen w-full flex items-center justify-center bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50 p-4">
        {bg}
        <motion.div
          key="confirm-pending"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="relative z-10 w-full max-w-md"
        >
          <div className="backdrop-blur-lg bg-white/70 border border-white/50 rounded-3xl shadow-2xl p-10 text-center space-y-6">
            {/* Icon */}
            <div className="flex justify-center">
              <div className="bg-gradient-to-br from-blue-500 to-purple-600 p-4 rounded-2xl shadow-lg">
                <Mail className="w-12 h-12 text-white" />
              </div>
            </div>

            <div>
              <h2 className="text-2xl font-semibold text-gray-800 mb-2">Check your email</h2>
              <p className="text-gray-600 text-sm">
                We sent a confirmation link to
              </p>
              <p className="font-semibold text-blue-600 mt-1 break-all">{pendingEmail}</p>
            </div>

            {/* Steps */}
            <div className="bg-blue-50 rounded-2xl p-4 text-left space-y-3">
              {[
                "Open the email from Supabase / your app",
                "Click the confirmation link",
                "Come back here and sign in",
              ].map((step, i) => (
                <div key={i} className="flex items-start gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-500 text-white text-xs flex items-center justify-center font-bold mt-0.5">
                    {i + 1}
                  </span>
                  <p className="text-sm text-gray-700">{step}</p>
                </div>
              ))}
            </div>

            {/* Feedback */}
            {error && (
              <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}
            {info && (
              <div className="flex items-center gap-2 p-3 bg-green-50 border border-green-200 rounded-xl text-green-700 text-sm">
                <CheckCircle className="w-4 h-4 shrink-0" />
                <span>{info}</span>
              </div>
            )}

            {/* Resend */}
            <button
              onClick={handleResendConfirmation}
              disabled={loading || resendCooldown > 0 || globalCooldown > 0}
              className="w-full bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 disabled:opacity-60 text-white py-3 px-6 rounded-xl shadow-md hover:shadow-lg transition-all duration-300 flex items-center justify-center gap-2"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              <span>
                {resendCooldown > 0
                  ? `Resend in ${resendCooldown}s`
                  : "Resend confirmation email"}
              </span>
            </button>

            {/* Back to sign in */}
            <button
              onClick={exitConfirmPending}
              className="w-full text-sm text-gray-500 hover:text-gray-700 underline transition-colors"
            >
              Back to sign in
            </button>
          </div>
        </motion.div>
        <style>{blobStyles}</style>
      </div>
    );
  }

  // ── Normal auth screen ────────────────────────────────────────────────
  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50 p-4">
      {bg}

      <motion.div
        key="auth"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="relative z-10"
      >
        <div className="backdrop-blur-lg bg-white/70 border border-white/50 rounded-3xl shadow-2xl p-12 w-full max-w-md">
          {/* Logo and Title */}
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.2, duration: 0.5 }}
            className="text-center mb-8"
          >
            <div className="flex justify-center mb-6">
              <div className="bg-gradient-to-br from-blue-500 to-purple-600 p-4 rounded-2xl shadow-lg">
                <Activity className="w-12 h-12 text-white" />
              </div>
            </div>
            <h1 className="text-3xl mb-2 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Fake Productivity Detector
            </h1>
            <p className="text-gray-600 text-sm">
              Analyze your activity and discover your true productivity
            </p>
          </motion.div>

          {/* Auth UI */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4, duration: 0.5 }}
            className="space-y-4"
          >
            {/* ── Google Button ───────────────────────────────────────── */}
            <button
              onClick={handleGoogleLogin}
              disabled={loading || globalCooldown > 0}
              className="w-full bg-white hover:bg-gray-50 text-gray-800 py-4 px-6 rounded-xl border-2 border-gray-200 shadow-md hover:shadow-lg transition-all duration-300 flex items-center justify-center gap-3 group disabled:opacity-60"
            >
              <Chrome className="w-5 h-5 text-blue-500 group-hover:scale-110 transition-transform duration-300" />
              <span>Sign in with Google</span>
            </button>

            {/* ── Divider ────────────────────────────────────────────── */}
            <div className="flex items-center gap-3">
              <div className="flex-1 h-px bg-gray-300" />
              <span className="text-xs text-gray-500 uppercase">or</span>
              <div className="flex-1 h-px bg-gray-300" />
            </div>

            {/* ── Tab Toggle ─────────────────────────────────────────── */}
            <div className="flex justify-center mb-2">
              <div className="bg-gray-100 p-1 rounded-lg flex">
                <button
                  onClick={() => { setTab("login"); setError(null); setPasswordErrors([]); }}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${tab === "login" ? "bg-white text-gray-800 shadow-sm" : "text-gray-600 hover:text-gray-800"
                    }`}
                >
                  Sign In
                </button>
                <button
                  onClick={() => { setTab("signup"); setError(null); setPasswordErrors([]); }}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${tab === "signup" ? "bg-white text-gray-800 shadow-sm" : "text-gray-600 hover:text-gray-800"
                    }`}
                >
                  Sign Up
                </button>
              </div>
            </div>

            {/* ── Error / Info Messages ──────────────────────────────── */}
            {error && (
              <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}
            {info && (
              <div className="flex items-center gap-2 p-3 bg-green-50 border border-green-200 rounded-xl text-green-700 text-sm">
                <CheckCircle className="w-4 h-4 shrink-0" />
                <span>{info}</span>
              </div>
            )}

            {/* ── Email Form ─────────────────────────────────────────── */}
            <form
              onSubmit={tab === "login" ? handleEmailLogin : handleEmailSignUp}
              className="space-y-4"
            >
              {tab === "signup" && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Full Name</label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <input
                      type="text"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      className="w-full pl-10 pr-4 py-3 border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all duration-300"
                      placeholder="Your full name"
                      required
                    />
                  </div>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full pl-10 pr-4 py-3 border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all duration-300"
                    placeholder="you@example.com"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Password</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => handlePasswordChange(e.target.value)}
                    className="w-full pl-10 pr-4 py-3 border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all duration-300"
                    placeholder={tab === "signup" ? "Min 4 chars, 2 numbers, 1 special" : "Enter your password"}
                    required
                  />
                </div>
                {tab === "signup" && passwordErrors.length > 0 && (
                  <ul className="mt-2 space-y-1">
                    {passwordErrors.map((err) => (
                      <li key={err} className="text-xs text-red-500 flex items-center gap-1">
                        <span className="inline-block w-1 h-1 rounded-full bg-red-400" />
                        {err}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <button
                type="submit"
                disabled={loading || globalCooldown > 0}
                className="w-full bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white py-4 px-6 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 flex items-center justify-center gap-2 disabled:opacity-60"
              >
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Mail className="w-5 h-5" />}
                <span>{tab === "login" ? "Sign In" : "Create Account"}</span>
              </button>
            </form>

            <p className="text-xs text-gray-500 text-center mt-6">
              Academic Project • Data Science & Web Technologies
            </p>
          </motion.div>
        </div>
      </motion.div>

      <style>{blobStyles}</style>
    </div>
  );
}
