import Link from "next/link";
import type { Metadata } from "next";
import type { Locale } from "@/lib/types";
import { getLocale } from "@/lib/locale";
import { translator } from "@/lib/i18n";
import { currentAccount } from "@/lib/session";
import { AssistantChat } from "@/components/assistant-chat";
import { EmptyState, Notice } from "@/components/states";

export const metadata: Metadata = { title: "المساعد — Smart-eCommerce" };

export default async function AssistantPage() {
  const locale: Locale = await getLocale();
  const t = translator(locale);
  const account = await currentAccount("customer");

  return (
    <main className="page page-narrow" id="main">
      <div className="page-head">
        <div>
          <p className="eyebrow">{t("nav.assistant")}</p>
          <h1>{t("assistant.title")}</h1>
          <p>{t("assistant.intro")}</p>
        </div>
      </div>
      <div className="stack-4">
        <Notice tone="info">{t("assistant.disclaimer")}</Notice>
        {account ? (
          <div className="panel">
            <AssistantChat locale={locale} />
          </div>
        ) : (
          <div className="stack-4">
            <EmptyState title={t("auth.requiredForCheckout")}>
              <Link className="btn btn-primary" href="/login?next=%2Fassistant">
                {t("auth.goLogin")}
              </Link>
              <Link className="btn btn-quiet" href="/register?next=%2Fassistant">
                {t("auth.goRegister")}
              </Link>
            </EmptyState>
          </div>
        )}
      </div>
    </main>
  );
}
