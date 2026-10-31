import type { Metadata } from "next";
import Link from "next/link";
import type { Locale } from "@/lib/types";
import { getLocale } from "@/lib/locale";
import { translator } from "@/lib/i18n";
import { VoiceSearchPanel } from "@/components/voice-search-panel";
import { Notice } from "@/components/states";

export const metadata: Metadata = { title: "البحث بالصوت — Smart-eCommerce" };

export default async function VoiceSearchPage() {
  const locale: Locale = await getLocale();
  const t = translator(locale);

  return (
    <main className="page page-narrow" id="main">
      <div className="page-head">
        <div>
          <p className="eyebrow">{t("search.voice")}</p>
          <h1>{t("voice.title")}</h1>
          <p>{t("voice.intro")}</p>
        </div>
        <Link className="btn btn-quiet" href="/">
          {t("voice.textFallback")}
        </Link>
      </div>
      <div className="stack-4">
        <Notice tone="info">{t("voice.intro")}</Notice>
        <VoiceSearchPanel locale={locale} />
      </div>
    </main>
  );
}