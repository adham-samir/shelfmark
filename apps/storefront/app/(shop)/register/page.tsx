import type { Metadata } from "next";
import { redirect } from "next/navigation";
import type { Locale } from "@/lib/types";
import { getLocale } from "@/lib/locale";
import { translator } from "@/lib/i18n";
import { currentAccount, safeNext } from "@/lib/session";
import { AuthForm } from "@/components/auth-form";

export const metadata: Metadata = { title: "إنشاء حساب — Smart-eCommerce" };

export default async function RegisterPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string | string[] }>;
}) {
  const locale: Locale = await getLocale();
  const t = translator(locale);
  const params = await searchParams;
  const next = safeNext(Array.isArray(params.next) ? params.next[0] : params.next) || "/account";

  if (await currentAccount("customer")) {
    redirect(next);
  }

  return (
    <main className="page page-narrow" id="main">
      <div className="page-head">
        <div>
          <p className="eyebrow">{t("nav.account")}</p>
          <h1>{t("auth.registerTitle")}</h1>
          <p>{t("auth.registerIntro")}</p>
        </div>
      </div>
      <div style={{ marginBlockStart: 18 }}>
        <AuthForm locale={locale} mode="register" next={next} />
      </div>
    </main>
  );
}
