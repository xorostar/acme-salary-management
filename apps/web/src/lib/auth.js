"use client";

import { useRouter } from "next/navigation";
import { createContext, createElement, useCallback, useContext, useEffect, useState } from "react";

import { api, session, setUnauthorizedHandler } from "@/lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const router = useRouter();
  // undefined = not read from storage yet (avoids a login-page flash on reload)
  const [user, setUser] = useState(undefined);

  useEffect(() => {
    // Reading sessionStorage must wait until mount: it does not exist during
    // server rendering, so this is the external-system sync effects are for.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setUser(session.token ? session.user : null);
    setUnauthorizedHandler(() => {
      setUser(null);
      router.replace("/login?expired=1");
    });
  }, [router]);

  const login = useCallback(async (email, password) => {
    const { token, user: u } = await api.login(email, password);
    session.save(token, u);
    setUser(u);
    return u;
  }, []);

  const logout = useCallback(() => {
    session.clear();
    setUser(null);
    router.replace("/login");
  }, [router]);

  const value = {
    user,
    ready: user !== undefined,
    isAdmin: user?.role === "hr_admin",
    login,
    logout,
  };
  return createElement(AuthContext.Provider, { value }, children);
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
