import Link from "next/link";
import { getLocale } from "@/lib/locale";
import { translator } from "@/lib/i18n";
import { api } from "@/lib/api";
import { currentAccount } from "@/lib/session";
import { Header } from "@/components/header";
import { SessionProvider } from "@/components/session-provider";

async function cartCount(): Promise<number> {
  try {
    const cart = await api.cart();
    return cart.items.reduce((total, item) => total + item.quantity, 0);
  } catch {
    return 0;
  }
}

export default async function ShopLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const locale = await getLocale();
  const t = translator(locale);
  const account = await currentAccount("customer");
  const items = account ? await cartCount() : 0;

  return (
    <SessionProvider
      value={{
        signedIn: account !== null,
        displayName: account?.profile?.display_name ?? null,
        cartCount: items,
      }}
    >
      <a className="skip-link" href="#main">
        {t("nav.skip")}
      </a>
      <div className="shell">
        <Header
          locale={locale}
          cartCount={items}
          signedIn={account !== null}
          accountName={account?.profile?.display_name ?? null}
        />
        {children}
        <footer className="site-footer">
          <div className="inner">
            <p>{t("common.footerNote")}</p>
            <nav aria-label={t("common.footerNav")}>
              <Link href="/assistant">{t("nav.assistant")}</Link>
              <Link href="/search/image">{t("search.image")}</Link>
              <Link href="/search/voice">{t("search.voice")}</Link>
              <Link href="/account">{t("nav.account")}</Link>
            </nav>
          </div>
        </footer>
      </div>
    </SessionProvider>
  );
}
