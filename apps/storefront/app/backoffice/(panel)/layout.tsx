import type { Metadata } from "next";
import Link from "next/link";
import type { Locale } from "@/lib/types";
import { getLocale } from "@/lib/locale";
import { translator } from "@/lib/i18n";
import { requireOperator } from "@/lib/session";
import { signOut } from "@/lib/auth-actions";
import { switchLocale } from "@/lib/actions";
import { IconCart, IconShield } from "@/components/icons";
import { OperatorNav, type NavItem } from "@/components/operator-nav";

export const metadata: Metadata = {
  title: "لوحة الإدارة — Smart-eCommerce",
  robots: { index: false, follow: false },
};

export default async function BackofficePanelLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const locale: Locale = await getLocale();
  const t = translator(locale);
  const account = await requireOperator("/backoffice");

  // Grouped by what the operator is trying to do, not by data model. "Overview"
  // is where you start, "Operations" is the daily queue, "Intelligence" is the
  // analysis you do less often.
  const groups: Array<{ label: string; items: NavItem[] }> = [
    {
      label: t("admin.groupOverview"),
      items: [{ href: "/backoffice", label: t("admin.dashboard"), icon: "grid" }],
    },
    {
      label: t("admin.groupOperations"),
      items: [
        { href: "/backoffice/orders", label: t("nav.orders"), icon: "cart" },
        { href: "/backoffice/inventory", label: t("nav.inventory"), icon: "inventory" },
        { href: "/backoffice/pricing", label: t("nav.pricing"), icon: "tag" },
      ],
    },
    {
      label: t("admin.groupIntelligence"),
      items: [
        { href: "/backoffice/segments", label: t("nav.segments"), icon: "segments" },
        { href: "/backoffice/risk", label: t("nav.risk"), icon: "shield" },
        { href: "/backoffice/analytics", label: t("nav.analytics"), icon: "chart" },
      ],
    },
  ];

  const principal = account.principal_id;
  const displayName = account.profile?.display_name ?? null;

  return (
    <div className="bo-shell">
      <div className="bo-body">
        <aside className="bo-rail" data-surface="rail" aria-label={t("admin.navLabel")}>
          <Link className="bo-rail-brand" href="/backoffice">
            <span className="mark" aria-hidden="true">
              SE
            </span>
            <span className="name">
              <strong>{t("admin.title")}</strong>
              <span>{t("brand.name")}</span>
            </span>
          </Link>

          <OperatorNav groups={groups} />

          <div className="bo-rail-footer">
            <Link href="/">
              <IconCart size={15} />
              <span>{t("admin.viewStorefront")}</span>
            </Link>
            <form action={signOut}>
              <input type="hidden" name="surface" value="operator" />
              <button type="submit">
                <IconShield size={15} />
                <span>{t("admin.signOut")}</span>
              </button>
            </form>
          </div>
        </aside>

        <div className="bo-content">
          <header className="bo-top">
            {/* The page owns its h1; the bar carries context only, so the
                document keeps a single top-level heading per route. */}
            <div className="bo-top-heading">
              <p className="bo-top-context">{t("admin.title")}</p>
              <p className="bo-top-note">{t("admin.operatorOnly")}</p>
            </div>
            <div className="bo-top-actions">
              <div className="bo-identity">
                {displayName ? (
                  <strong dir="auto">{displayName}</strong>
                ) : null}
                {/* The principal id stays available but stops being the
                    loudest text on every page. */}
                <code dir="ltr" title={t("admin.signedInAs")}>
                  {principal}
                </code>
              </div>
              <form action={switchLocale}>
                <input type="hidden" name="locale" value={locale === "ar" ? "en" : "ar"} />
                <button type="submit" className="locale-switch" aria-label={t("locale.switch")}>
                  {t("locale.switch")}
                </button>
              </form>
            </div>
          </header>
          {children}
        </div>
      </div>
    </div>
  );
}
