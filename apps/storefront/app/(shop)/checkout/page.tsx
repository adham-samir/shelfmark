import Link from "next/link";
import type { Metadata } from "next";
import type { Locale, Product } from "@/lib/types";
import { api } from "@/lib/api";
import { getLocale } from "@/lib/locale";
import { translator } from "@/lib/i18n";
import { EmptyState, ErrorState, Notice } from "@/components/states";
import { CheckoutForm } from "@/components/checkout-form";
import { requireCustomer } from "@/lib/session";

export const metadata: Metadata = { title: "الدفع" };

export default async function CheckoutPage() {
  const locale: Locale = await getLocale();
  const t = translator(locale);
  await requireCustomer("/checkout");

  try {
    const [cart, catalog, addresses] = await Promise.all([
      api.cart(),
      api.products({ limit: 100 }),
      // A missing address book must never block checkout.
      api.addresses().catch(() => null),
    ]);
    const names: Record<string, string> = {};
    for (const product of catalog.items as Product[]) {
      names[product.product_id] = product.name;
    }

    if (!cart.items.length) {
      return (
        <main className="page page-narrow" id="main">
          <div className="page-head">
            <div>
              <p className="eyebrow">{t("checkout.title")}</p>
              <h1>{t("checkout.title")}</h1>
            </div>
          </div>
          <div className="stack-4">
            <EmptyState title={t("checkout.emptyCart")} hint={t("cart.emptyHint")}>
              <Link className="btn btn-primary" href="/">
                {t("cart.browse")}
              </Link>
            </EmptyState>
          </div>
        </main>
      );
    }

    return (
      <main className="page" id="main">
        <div className="page-head">
          <div>
            <p className="eyebrow">{t("checkout.title")}</p>
            <h1>{t("checkout.title")}</h1>
            <p>{t("checkout.intro")}</p>
          </div>
          <Link className="btn btn-quiet" href="/cart">
            {t("cart.title")}
          </Link>
        </div>
        <div className="stack-5">
          <Notice tone="warn">{t("checkout.riskNote")}</Notice>
          <div className="spacer-4" />
          <CheckoutForm
            locale={locale}
            cart={cart}
            names={names}
            defaultAddress={
              addresses?.items.find((item) => item.is_default) ?? null
            }
          />
        </div>
      </main>
    );
  } catch {
    return (
      <main className="page page-narrow" id="main">
        <ErrorState
          locale={locale}
          title={t("checkout.failed")}
          hint={t("listing.loadErrorHint")}
          onRetryHref="/checkout"
        />
      </main>
    );
  }
}