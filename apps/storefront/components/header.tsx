import Link from "next/link";
import type { Locale } from "@/lib/types";
import { translator } from "@/lib/i18n";
import { switchLocale } from "@/lib/actions";
import {
  IconAssistant,
  IconCamera,
  IconCart,
  IconMic,
  IconPin,
  IconSearch,
  IconUser,
} from "./icons";

export function Header({
  locale,
  cartCount,
  signedIn,
  accountName,
}: {
  locale: Locale;
  cartCount: number;
  signedIn: boolean;
  accountName: string | null;
}) {
  const t = translator(locale);

  return (
    <header className="site-header">
      <div className="header-inner">
        <Link className="brand" href="/">
          <strong>{t("brand.name")}</strong>
          <span>{t("brand.sub")}</span>
        </Link>

        <form className="header-search" action="/" method="get" role="search">
          <span className="field">
            <IconSearch size={17} aria-hidden="true" />
            <label className="visually-hidden" htmlFor="site-search">
              {t("search.label")}
            </label>
            <input
              id="site-search"
              type="search"
              name="q"
              placeholder={t("search.placeholder")}
              autoComplete="off"
            />
          </span>
          <Link className="search-mode" href="/search/voice" title={t("search.voice")}>
            <IconMic size={16} />
            <span className="visually-hidden">{t("search.voice")}</span>
          </Link>
          <Link className="search-mode" href="/search/image" title={t("search.image")}>
            <IconCamera size={16} />
            <span className="visually-hidden">{t("search.image")}</span>
          </Link>
          <button className="search-submit" type="submit">
            {t("search.submit")}
          </button>
        </form>

        <div className="header-actions">
          <form action={switchLocale} className="header-action" style={{ paddingInline: 12 }}>
            <input type="hidden" name="locale" value={locale === "ar" ? "en" : "ar"} />
            <button type="submit" className="locale-switch" aria-label={t("locale.switch")}>
              <span aria-hidden="true" lang={locale === "ar" ? "en" : "ar"} dir={locale === "ar" ? "ltr" : "rtl"}>
                {t("locale.switch")}
              </span>
            </button>
          </form>

          <Link
            className="header-action"
            href="/assistant"
            title={t("nav.assistant")}
            aria-label={t("nav.assistant")}
          >
            <IconAssistant size={17} />
            <span className="label">{t("nav.assistant")}</span>
          </Link>

          <span className="header-action" title={t("nav.locationLabel")}>
            <IconPin size={17} />
            <span className="label">{t("nav.location")}</span>
          </span>

          <Link
            className="header-action"
            href={signedIn ? "/account" : "/login"}
            title={t("nav.accountLabel")}
            aria-label={t("nav.accountLabel")}
          >
            <IconUser size={17} />
            <span className="label">{accountName ?? t("nav.account")}</span>
          </Link>

          <Link
            className="header-action"
            href="/cart"
            aria-label={t("nav.cartLabel", { count: cartCount })}
          >
            <IconCart size={17} />
            <span className="label">
              {t("nav.cart")} (<strong>{cartCount}</strong>)
            </span>
          </Link>
        </div>
      </div>
    </header>
  );
}
