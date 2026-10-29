import type { Metadata } from "next";
import Link from "next/link";
import type { Locale } from "@/lib/types";
import { getLocale } from "@/lib/locale";
import { translator } from "@/lib/i18n";
import { requireOperator } from "@/lib/session";
import { signOut } from "@/lib/auth-actions";
import { switchLocale } from "@/lib/actions";
import {
  IconCart,
  IconChart,
  IconGrid,
  IconInventory,
  IconSegments,
  IconShield,
  IconTag,
} from "@/components/icons";

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

  const sections = [
    { href: "/backoffice", label: t("admin.dashboard"), Icon: IconGrid },
    { href: "/backoffice/orders", label: t("nav.orders"), Icon: IconCart },
    { href: "/backoffice/inventory", label: t("nav.inventory"), Icon: IconInventory },
    { href: "/backoffice/pricing", label: t("nav.pricing"), Icon: IconTag },
    { href: "/backoffice/segments", label: t("nav.segments"), Icon: IconSegments },
    { href: "/backoffice/risk", label: t("nav.risk"), Icon: IconShield },
    { href: "/backoffice/analytics", label: t("nav.analytics"), Icon: IconChart },
  ];

  return (
    <div className="bo-shell">
      <header className="bo-top">
        <Link className="brand" href="/backoffice">
          <strong>{t("admin.title")}</strong>
          <span>{t("brand.name")}</span>
        </Link>
        <div className="bo-top-actions">
          <span className="bo-identity">
            <span className="visually-hidden">{t("admin.signedInAs")} </span>
            <span dir="ltr">{account.profile?.display_name ?? account.principal_id}</span>
          </span>
          <form action={switchLocale}>
            <input type="hidden" name="locale" value={locale === "ar" ? "en" : "ar"} />
            <button type="submit" className="btn btn-quiet">
              {t("locale.switch")}
            </button>
          </form>
          <Link className="btn btn-quiet" href="/">
            {t("admin.viewStorefront")}
          </Link>
          <form action={signOut}>
            <input type="hidden" name="surface" value="operator" />
            <button className="btn" type="submit">
              {t("admin.signOut")}
            </button>
          </form>
        </div>
      </header>

      <div className="bo-body">
        <nav className="bo-nav" aria-label={t("admin.navLabel")}>
          {sections.map(({ href, label, Icon }) => (
            <Link key={href} href={href}>
              <Icon size={16} />
              <span>{label}</span>
            </Link>
          ))}
        </nav>
        <div className="bo-content">{children}</div>
      </div>
    </div>
  );
}
