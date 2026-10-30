"use client";

import { createContext, useCallback, useContext, useMemo, useState } from "react";

export interface SessionValue {
  signedIn: boolean;
  displayName: string | null;
  /** Live cart quantity, seeded from the server render and updated on add. */
  cartCount: number;
  /** Adds to the badge without waiting for a server refresh. */
  incrementCart: (by?: number) => void;
  /** Re-syncs the badge after a server refresh reports a new total. */
  setCartCount: (value: number) => void;
}

const SessionContext = createContext<SessionValue>({
  signedIn: false,
  displayName: null,
  cartCount: 0,
  incrementCart: () => {},
  setCartCount: () => {},
});

export function SessionProvider({
  value,
  children,
}: {
  value: { signedIn: boolean; displayName: string | null; cartCount: number };
  children: React.ReactNode;
}) {
  const [cartCount, setCartCount] = useState(value.cartCount);

  const incrementCart = useCallback((by = 1) => {
    setCartCount((current) => Math.max(0, current + by));
  }, []);

  const contextValue = useMemo<SessionValue>(
    () => ({
      signedIn: value.signedIn,
      displayName: value.displayName,
      cartCount,
      incrementCart,
      setCartCount,
    }),
    [value.signedIn, value.displayName, cartCount, incrementCart],
  );

  return (
    <SessionContext.Provider value={contextValue}>{children}</SessionContext.Provider>
  );
}

export function useSession(): SessionValue {
  return useContext(SessionContext);
}
