import type { Metadata } from "next";
import Link from "next/link";
import type { Locale } from "@/lib/types";
import { api } from "@/lib/api";
import { getLocale } from "@/lib/locale";
import { statusLabel, translator } from "@/lib/i18n";
import { formatDate, formatDateTime, formatMoney } from "@/lib/format";
import { requireCustomer } from "@/lib/session";
import { signOut } from "@/lib/auth-actions";
import { AccountForm } from "@/components/account-form";
import { PasswordForm } from "@/components/password-form";
import { EmptyState, Notice } from "@/components/states";

export const metadata: Metadata = { title: "حسابي — Smart-eCommerce" };

export default async function AccountPage() {
  const locale: Locale = await getLocale();
  const t = translator(locale);
  const account = await requireCustomer("/account");
  const profile = account.profile;

  if (!profile) {
    return (
      <main className="page page-narrow" id="main">
        <Notice tone="error">{t("account.failed")}</Notice>
      </main>
    );
  }

  let recent;
  try {
    recent = await api.orders({ limit: 3 });
  } catch {
    recent = null;
  }

  return (
    <main className="page page-narrow" id="main">
      <div className="page-head">
        <div>
          <p className="eyebrow">{t("nav.account")}</p>
          <h1>{t("account.title")}</h1>
          <p>{t("account.intro")}</p>
        </div>
        <form action={signOut}>
          <input type="hidden" name="surface" value="customer" />
          <button className="btn btn-quiet" type="submit">
            {t("auth.signOut")}
          </button>
        </form>
      </div>

      <div className="split" style={{ marginBlockStart: 18 }}>
        <AccountForm locale={locale} profile={profile} />

        <div>
          <section className="panel" aria-labelledby="account-summary">
            <h2 id="account-summary">{t("account.title")}</h2>
            <dl className="detail-specs" style={{ marginBlockStart: 0 }}>
              <div>
                <dt>{t("account.email")}</dt>
                <dd dir="ltr">{profile.email}</dd>
              </div>
              <div>
                <dt>{t("account.memberSince")}</dt>
                <dd>{formatDate(profile.member_since, locale)}</dd>
              </div>
              <div>
                <dt>{t("account.orderCount")}</dt>
                <dd>{profile.order_count}</dd>
              </div>
            </dl>
            <Link
              className="btn btn-quiet btn-block"
              href="/account/addresses"
              style={{ marginBlockStart: 12 }}
            >
              {t("account.addresses")}
            </Link>
          </section>

          <section className="panel" aria-labelledby="account-recent-orders">
            <h2 id="account-recent-orders">{t("account.recentOrders")}</h2>
            {recent === null ? (
              <p className="field-hint">{t("orders.signIn")}</p>
            ) : recent.items.length === 0 ? (
              <EmptyState title={t("account.emptyOrders")}>
                <Link className="btn btn-dark" href="/">
                  {t("cart.browse")}
                </Link>
              </EmptyState>
            ) : (
              <>
                <ul className="summary-lines">
                  {recent.items.map((order) => (
                    <li key={order.order_id}>
                      <span>
                        <Link href={`/orders/${order.order_id}`}>
                          <span dir="ltr">{order.order_id.slice(0, 8)}</span>
                        </Link>
                        {" · "}
                        {formatDateTime(order.created_at, locale)}
                      </span>
                      <span className="price-amount">
                        {formatMoney(order.subtotal, locale)} {order.currency}
                      </span>
                      <span className="pill" data-status={order.status}>
                        {statusLabel(t, order.status)}
                      </span>
                    </li>
                  ))}
                </ul>
                <Link
                  className="btn btn-block"
                  href="/account/orders"
                  style={{ marginBlockStart: 12 }}
                >
                  {t("account.viewAll")}
                </Link>
              </>
            )}
          </section>
        </div>
      </div>

      <div className="split" style={{ marginBlockStart: 18 }}>
        <PasswordForm locale={locale} />
      </div>
    </main>
  );
}
