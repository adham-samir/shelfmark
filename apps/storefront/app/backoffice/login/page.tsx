import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import type { Locale } from "@/lib/types";
import { getLocale } from "@/lib/locale";
import { translator } from "@/lib/i18n";
import { currentAccount, safeNext } from "@/lib/session";
import { AuthForm } from "@/components/auth-form";

export const metadata: Metadata = { title: "دخول لوحة الإدارة" };

export default async function BackofficeLoginPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string | string[] }>;
}) {
  const locale: Locale = await getLocale();
  const t = translator(locale);
  const params = await searchParams;
  const next = safeNext(Array.isArray(params.next) ? params.next[0] : params.next) || "/backoffice";

  if (await currentAccount("operator")) {
    redirect(next.startsWith("/backoffice") && !next.startsWith("/backoffice/login") ? next : "/backoffice");
  }

  return (
    <main className="page page-narrow" id="main">
      <div className="page-head">
        <div>
          <p className="eyebrow">{t("nav.backoffice")}</p>
          <h1>{t("auth.operatorTitle")}</h1>
          <p>{t("auth.operatorIntro")}</p>
        </div>
      </div>
      <div className="stack-4">
        <AuthForm locale={locale} mode="operator" next={next} />
        <p className="auth-switch stack-4">
          <Link href="/">{t("admin.viewStorefront")}</Link>
        </p>
      </div>
    </main>
  );
}
