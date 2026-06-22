"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { setApiUser } from "./api";
import type { Role } from "./types";

export const USERS: Record<Role, { username: string; display: string }> = {
  supervisor: { username: "s.vega", display: "S. Vega" },
  technician: { username: "a.lang", display: "A. Lang" },
  quality_engineer: { username: "q.idris", display: "Q. Idris" },
  plant_admin: { username: "p.okoro", display: "P. Okoro" },
};

export const ROLE_LABEL: Record<Role, string> = {
  supervisor: "Supervisor",
  technician: "Technician",
  quality_engineer: "Quality Engineer",
  plant_admin: "Plant Admin",
};

interface RoleCtx {
  role: Role;
  username: string;
  setRole: (r: Role) => void;
}

const Ctx = createContext<RoleCtx | null>(null);

export function RoleProvider({ children }: { children: React.ReactNode }) {
  const [role, setRoleState] = useState<Role>("supervisor");

  useEffect(() => {
    const stored = (typeof window !== "undefined" && localStorage.getItem("vra-role")) as Role | null;
    if (stored && USERS[stored]) {
      setRoleState(stored);
      setApiUser(USERS[stored].username);
    } else {
      setApiUser(USERS.supervisor.username);
    }
  }, []);

  const setRole = (r: Role) => {
    setRoleState(r);
    setApiUser(USERS[r].username);
    if (typeof window !== "undefined") localStorage.setItem("vra-role", r);
  };

  return <Ctx.Provider value={{ role, username: USERS[role].username, setRole }}>{children}</Ctx.Provider>;
}

export function useRole(): RoleCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error("useRole must be used within RoleProvider");
  return c;
}
