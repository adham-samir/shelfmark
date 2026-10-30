"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  IconCart,
  IconChart,
  IconGrid,
  IconInventory,
  IconSegments,
  IconShield,
  IconTag,
} from "./icons";

/**
 * Icon lookup keyed by string so the server layout can describe the navigation
 * as plain data. Component references cannot cross the server/client boundary,
 * and resolving them here keeps the active-state logic in one client file.
 */
const ICONS = {
  grid: IconGrid,
  cart: IconCart,
  inventory: IconInventory,
  tag: IconTag,
  segments: IconSegments,
  shield: IconShield,
  chart: IconChart,
} as const;

export type NavIcon = keyof typeof ICONS;

export type NavItem = {
  href: string;
  label: string;
  icon: NavIcon;
};

/**
 * Back-office navigation with a real current-page state.
 *
 * Pathname matching is exact for the dashboard and prefix-based for sections, so
 * `/backoffice/orders/abc` still marks "Orders" as current.
 */
export function OperatorNav({
  groups,
}: {
  groups: Array<{ label: string; items: NavItem[] }>;
}) {
  const pathname = usePathname() ?? "";

  const isActive = (href: string) =>
    href === "/backoffice" ? pathname === "/backoffice" : pathname.startsWith(href);

  return (
    <nav className="bo-nav">
      {groups.map((group) => (
        <div className="bo-nav-group" key={group.label}>
          <h2>{group.label}</h2>
          {group.items.map(({ href, label, icon }) => {
            const Icon = ICONS[icon];
            return (
              <Link
                key={href}
                href={href}
                aria-current={isActive(href) ? "page" : undefined}
              >
                <Icon size={16} aria-hidden="true" />
                <span>{label}</span>
              </Link>
            );
          })}
        </div>
      ))}
    </nav>
  );
}
