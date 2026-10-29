"use client";

import { createContext, useContext } from "react";

export interface SessionValue {
  signedIn: boolean;
  displayName: string | null;
}

const SessionContext = createContext<SessionValue>({
  signedIn: false,
  displayName: null,
});

export function SessionProvider({
  value,
  children,
}: {
  value: SessionValue;
  children: React.ReactNode;
}) {
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionValue {
  return useContext(SessionContext);
}
