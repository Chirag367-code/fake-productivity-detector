/**
 * Backend API Configuration
 *
 * Configures the connection to the Python FastAPI backend.
 * Automatically attaches the Supabase access token to requests.
 */

import { supabase } from "../../lib/supabase";

// Backend API base URL
export const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8000";

// API endpoints
export const API_ENDPOINTS = {
  // Analysis
  analyze: `${API_BASE_URL}/api/v1/analyze`,
  analyzeQuick: `${API_BASE_URL}/api/v1/analyze/quick`,

  // History
  history: (userId: string) => `${API_BASE_URL}/api/v1/history/${userId}`,
  historyStats: (userId: string) =>
    `${API_BASE_URL}/api/v1/history/${userId}/stats`,
  historyTrend: (userId: string) =>
    `${API_BASE_URL}/api/v1/history/${userId}/trend`,

  // Reports
  reports: (userId: string) => `${API_BASE_URL}/api/v1/reports/${userId}`,
  weeklyReport: (userId: string) =>
    `${API_BASE_URL}/api/v1/reports/${userId}/weekly`,
  comparison: (userId: string) =>
    `${API_BASE_URL}/api/v1/reports/${userId}/comparison`,
  exportCsv: (userId: string) =>
    `${API_BASE_URL}/api/v1/reports/${userId}/export/csv`,

  // CSV Upload
  uploadCsv: `${API_BASE_URL}/api/v1/upload-csv`,
  csvTemplate: `${API_BASE_URL}/api/v1/upload-csv/template`,
  validateCsv: `${API_BASE_URL}/api/v1/upload-csv/validate`,

  // Health
  health: `${API_BASE_URL}/health`,
  info: `${API_BASE_URL}/info`,
};

/**
 * Returns the current Supabase access token (or empty string).
 * Call this before every API request so the backend can authenticate.
 */
async function getAccessToken(): Promise<string> {
  try {
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token ?? "";
  } catch {
    return "";
  }
}

// Helper function for API calls
export async function apiCall<T>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  const token = await getAccessToken();

  const defaultHeaders: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (token) {
    defaultHeaders["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({
      detail: response.statusText,
    }));
    throw new Error(error.detail || "API request failed");
  }

  return response.json();
}

/**
 * A drop-in replacement for `fetch` that automatically attaches
 * the Supabase access token as a Bearer header.
 * Use this instead of raw `fetch(API_ENDPOINTS.xxx, ...)`.
 */
export async function authFetch(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = await getAccessToken();

  const headers = new Headers(options.headers);
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  return fetch(url, { ...options, headers });
}
