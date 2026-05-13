"use client";

import * as React from "react";
import { extractError } from "../lib/extract-error";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

export type AuthUser = { user_id: number; username: string; is_mod: boolean; email_verified: boolean };

type AuthState = {
  user: AuthUser | null;
  token: string | null;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = React.createContext<AuthState>({
  user: null,
  token: null,
  login: async () => {},
  register: async () => {},
  logout: () => {},
});

const TOKEN_KEY = "rough_draft_token";
const USER_KEY = "rough_draft_user";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  // Always start null so server and client render the same initial HTML.
  // Rehydrate from localStorage in an effect (client-only).
  const [token, setToken] = React.useState<string | null>(null);
  const [user, setUser] = React.useState<AuthUser | null>(null);

  React.useEffect(() => {
    function loadFromStorage() {
      const storedToken = window.localStorage.getItem(TOKEN_KEY);
      const storedUser = window.localStorage.getItem(USER_KEY);
      if (storedToken) setToken(storedToken);
      if (storedUser) {
        try { setUser(JSON.parse(storedUser)); } catch { /* ignore corrupt data */ }
      }
    }
    loadFromStorage();
    window.addEventListener("storage", loadFromStorage);
    return () => window.removeEventListener("storage", loadFromStorage);
  }, []);

  function persist(t: string, u: AuthUser) {
    window.localStorage.setItem(TOKEN_KEY, t);
    window.localStorage.setItem(USER_KEY, JSON.stringify(u));
    setToken(t);
    setUser(u);
    // Fire-and-forget: migrate any anonymous votes to this account
    fetch(`${API_BASE}/auth/claim-anon-votes`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${t}`,
        "X-Client-Id": window.localStorage.getItem("rough_draft_client_id") ?? "",
      },
    }).catch(() => {});
  }

  function logout() {
    window.localStorage.removeItem(TOKEN_KEY);
    window.localStorage.removeItem(USER_KEY);
    setToken(null);
    setUser(null);
  }

  async function login(username: string, password: string) {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(extractError(err, "Login failed"));
    }
    const data = await res.json();
    persist(data.access_token, { user_id: data.user_id, username: data.username, is_mod: data.is_mod ?? false, email_verified: data.email_verified ?? false });
  }

  async function register(username: string, email: string, password: string) {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, email, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(extractError(err, "Registration failed"));
    }
    const data = await res.json();
    persist(data.access_token, { user_id: data.user_id, username: data.username, is_mod: data.is_mod ?? false, email_verified: data.email_verified ?? false });
  }

  return (
    <AuthContext.Provider value={{ user, token, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return React.useContext(AuthContext);
}
