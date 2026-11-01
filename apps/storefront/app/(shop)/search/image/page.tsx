import type { Metadata } from "next";
import Link from "next/link";
import type { Locale } from "@/lib/types";
import { getLocale } from "@/lib/locale";
import { translator } from "@/lib/i18n";
import { ImageSearchPanel } from "@/components/image-search-panel";
import { Notice } from "@/components/states";

export const metadata: Metadata = { title: "البحث بالصورة" };

export default async function ImageSearchPage() {
  const locale: Locale = await getLocale();
  const t = translator(locale);

  return (
    <main className="page page-narrow" id="main">
      <div className="page-head">
        <div>
          <p className="eyebrow">{t("search.image")}</p>
          <h1>{t("image.title")}</h1>
          <p>{t("image.intro")}</p>
        </div>
        <Link className="btn btn-quiet" href="/">
          {t("image.fallback")}
        </Link>
      </div>
      <div className="stack-4">
        <Notice tone="info">{t("image.syntheticNote")}</Notice>
        <ImageSearchPanel locale={locale} />
      </div>
    </main>
  );
}