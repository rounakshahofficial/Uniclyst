import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { User } from "../types";
import { get, post, setToken } from "./api";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<User>;
  register: (data: {
    username: string;
    email: string;
    password: string;
    full_name: string;
    college_id?: number;
  }) => Promise<User>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!localStorage.getItem("uniclyst_token")) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      setUser(await get<User>("/users/me"));
    } catch {
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const login = useCallback(async (username: string, password: string) => {
    const data = await post<{ access_token: string; user: User }>("/auth/login", {
      username,
      password,
    });
    setToken(data.access_token);
    setUser(data.user);
    return data.user;
  }, []);

  const register = useCallback(
    async (payload: {
      username: string;
      email: string;
      password: string;
      full_name: string;
      college_id?: number;
    }) => {
      // NOTE: there is intentionally no role field — public registration
      // always creates a student account (enforced by the backend too).
      const data = await post<{ access_token: string; user: User }>("/auth/register", payload);
      setToken(data.access_token);
      setUser(data.user);
      return data.user;
    },
    []
  );

  const logout = useCallback(async () => {
    try {
      await post("/auth/logout");
    } catch {
      /* token may already be invalid */
    }
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
