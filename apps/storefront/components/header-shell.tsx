"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Adds `data-condensed="true"` to the storefront header once the page has
 * scrolled past `threshold`, so the header can shrink without a scroll listener
 * measuring layout on every frame.
 *
 * A sentinel element placed at the top of the page is observed instead: when it
 * leaves the viewport the header is condensed. That costs one callback per
 * crossing rather than one per scroll event.
 */
export function HeaderShell({
  threshold = 24,
  children,
}: {
  threshold?: number;
  children: React.ReactNode;
}) {
  const [condensed, setCondensed] = useState(false);
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) return;

    const observer = new IntersectionObserver(
      ([entry]) => setCondensed(!entry.isIntersecting),
      { rootMargin: `-${threshold}px 0px 0px 0px`, threshold: 0 },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [threshold]);

  return (
    <>
      <div ref={sentinelRef} aria-hidden="true" className="header-sentinel" />
      <header className="site-header" data-condensed={condensed ? "true" : "false"}>
        {children}
      </header>
    </>
  );
}
