import Link from "next/link";
import type { Metadata } from "next";
import type { Locale, OrderSummary } from "@/lib/types";
import { api } from "@/lib/api";
import { getLocale } from "@/lib/locale";
import { translator } from "@/lib/i18n";
import { currentAccount } from "@/lib/session";
import { AssistantChat } from "@/components/assistant-chat";
import { EmptyState, Notice } from "@/components/states";

export const metadata: Metadata = { title: "نور" };

export default async function AssistantPage() {
  const locale: Locale = await getLocale();
  const t = translator(locale);
  const account = await currentAccount("customer");

  // The last few orders power the attach picker. A failure here must not take
  // the whole assistant down, so it degrades to an empty picker.
  let recentOrders: OrderSummary[] = [];
  if (account) {
    try {
      recentOrders = (await api.orders({ limit: 3 })).items;
    } catch {
      recentOrders = [];
    }
  }

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
            <AssistantChat locale={locale} orders={recentOrders} />
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
