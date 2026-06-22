"use client";

import { QueryProvider } from "@/lib/query";
import { RoleProvider } from "@/lib/role";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <RoleProvider>
      <QueryProvider>{children}</QueryProvider>
    </RoleProvider>
  );
}
