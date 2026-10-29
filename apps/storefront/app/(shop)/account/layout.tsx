import type { Metadata } from "next";
import Link from "next/link";
import type { Locale } from "@/lib/types";
import { getLocale } from "@/lib/locale";
import { translator } from "@/lib/i18n";
import { requireCustomer } from "@/lib/session";

export const metadata: Metadata = { title: "حسابي — Smart-eCommerce" };

export default async function AccountLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const locale: Locale = await getLocale();
  const t = translator(locale);
  const account = await requireCustomer("/account");

  return (
    <>
      <div className="account-nav-wrap">
        <nav className="account-nav" aria-label={t("account.title")}>
          <span className="account-nav-name">{account.profile?.display_name}</span>
          <Link href="/account">{t("account.profile")}</Link>
          <Link href="/account/orders">{t("orders.title")}</Link>
          <Link href="/">{t("admin.viewStorefront")}</Link>
        </nav>
      </div>
      {children}
    </>
  );
}
