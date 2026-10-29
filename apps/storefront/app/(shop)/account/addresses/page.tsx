import type { Metadata } from "next";
import Link from "next/link";
import { api } from "@/lib/api";
import { translator } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";
import type { AddressList, Locale } from "@/lib/types";
import { requireCustomer } from "@/lib/session";
import { AddressCard, AddressForm } from "@/components/address-book";
import { EmptyState } from "@/components/states";

export const metadata: Metadata = { title: "عناويني — Smart-eCommerce" };

export default async function AddressesPage() {
  const locale: Locale = await getLocale();
  const t = translator(locale);
  await requireCustomer("/account/addresses");

  let book: AddressList | null = null;
  try {
    book = await api.addresses();
  } catch {
    book = null;
  }

  return (
    <main className="page page-narrow" id="main">
      <div className="page-head">
        <div>
          <p className="eyebrow">{t("nav.account")}</p>
          <h1>{t("addresses.title")}</h1>
          <p>{t("addresses.intro")}</p>
        </div>
        <Link className="btn btn-quiet" href="/account">
          {t("common.back")}
        </Link>
      </div>

      {book === null ? (
        <div style={{ marginBlockStart: 18 }}>
          <EmptyState
            title={t("addresses.loadFailed")}
            hint={t("addresses.loadFailedHint")}
          />
        </div>
      ) : (
        <div style={{ marginBlockStart: 18, display: "grid", gap: 18 }}>
          {book.items.length === 0 ? (
            <EmptyState
              title={t("addresses.empty")}
              hint={t("addresses.emptyHint")}
            />
          ) : (
            book.items.map((address) => (
              <AddressCard
                key={address.address_id}
                locale={locale}
                address={address}
              />
            ))
          )}

          {book.items.length >= book.limit ? (
            <p className="field-hint">
              {t("addresses.full", { count: book.limit })}
            </p>
          ) : (
            <AddressForm locale={locale} />
          )}
        </div>
      )}
    </main>
  );
}
