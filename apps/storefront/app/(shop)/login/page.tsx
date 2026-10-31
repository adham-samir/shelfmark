import type { Metadata } from "next";
import { redirect } from "next/navigation";
import type { Locale } from "@/lib/types";
import { getLocale } from "@/lib/locale";
import { translator } from "@/lib/i18n";
import { currentAccount, safeNext } from "@/lib/session";
import { AuthForm } from "@/components/auth-form";

export const metadata: Metadata = { title: "تسجيل الدخول — Smart-eCommerce" };

export default async function LoginPage({
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
          <h1>{t("auth.loginTitle")}</h1>
          <p>{t("auth.loginIntro")}</p>
        </div>
      </div>
      <div className="stack-4">
        <AuthForm locale={locale} mode="login" next={next} />
      </div>
    </main>
  );
}
