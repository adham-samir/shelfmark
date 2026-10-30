"use client";

import { useMemo, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import type { Address, Cart, Locale } from "@/lib/types";
import { translator } from "@/lib/i18n";
import { formatMoney, multiplyMoney, sumMoney } from "@/lib/format";

const TOKENS = [
  { value: "tok_sandbox_safe-1", label: { ar: "دفع عادي (يُقبل)", en: "Normal payment (accepted)" } },
  { value: "tok_sandbox_risk-high-1", label: { ar: "طلب مرتفع المخاطر (مراجعة)", en: "High-risk order (manual review)" } },
  { value: "tok_sandbox_risk-fail-1", label: { ar: "فشل تقييم المخاطر (مراجعة)", en: "Assessment failure (manual review)" } },
] as const;

interface FormState {
  recipient_name: string;
  phone: string;
  city: string;
  address_line: string;
  payment_token: string;
}

function idempotencyKey(): string {
  const stored = window.sessionStorage.getItem("smart_ecommerce_checkout_key");
  if (stored && stored.length >= 16) return stored;
  const key = `${crypto.randomUUID()}-${crypto.randomUUID()}`;
  window.sessionStorage.setItem("smart_ecommerce_checkout_key", key);
  return key;
}

export function CheckoutForm({
  locale,
  cart,
  names,
  defaultAddress,
}: {
  locale: Locale;
  cart: Cart;
  names: Record<string, string>;
  defaultAddress: Address | null;
}) {
  const t = translator(locale);
  const router = useRouter();
  const [form, setForm] = useState<FormState>({
    recipient_name: defaultAddress?.recipient_name ?? "",
    phone: defaultAddress?.phone ?? "",
    city: defaultAddress?.city ?? "القاهرة",
    address_line: defaultAddress?.address_line ?? "",
    payment_token: TOKENS[0].value,
  });
  // Opt-in: an address is only stored when the customer asks for it.
  const [saveAddress, setSaveAddress] = useState(false);
  const [errors, setErrors] = useState<Partial<Record<keyof FormState, string>>>({});
  const [failure, setFailure] = useState<{ code: string; message: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const subtotal = useMemo(() => sumMoney(cart.items.map((item) => multiplyMoney(item.unit_price, item.quantity))), [cart.items]);

  const set = (field: keyof FormState, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
  };

  const validate = (): boolean => {
    const next: Partial<Record<keyof FormState, string>> = {};
    if (form.recipient_name.trim().length < 2) next.recipient_name = t("checkout.nameError");
    if (!/^\+?[0-9][0-9 -]{6,19}$/.test(form.phone.trim())) next.phone = t("checkout.phoneError");
    if (form.city.trim().length < 2) next.city = t("checkout.cityError");
    if (form.address_line.trim().length < 5) next.address_line = t("checkout.addressError");
    if (!/^tok_sandbox_[A-Za-z0-9_-]{4,100}$/.test(form.payment_token)) {
      next.payment_token = t("checkout.tokenError");
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!validate()) return;
    setBusy(true);
    setFailure(null);
    try {
      const response = await fetch("/api/checkout", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          payment_token: form.payment_token,
          idempotency_key: idempotencyKey(),
          shipping: {
            recipient_name: form.recipient_name.trim(),
            phone: form.phone.trim(),
            city: form.city.trim(),
            address_line: form.address_line.trim(),
          },
          save_address: saveAddress,
        }),
      });
      const payload = (await response.json().catch(() => null)) as
        | { order_id?: string; status?: string; error?: { code?: string; message?: string } }
        | null;
      if (!response.ok || !payload?.order_id) {
        setFailure({
          code: payload?.error?.code ?? "unknown",
          message: payload?.error?.message ?? t("checkout.failed"),
        });
        return;
      }
      window.sessionStorage.removeItem("smart_ecommerce_checkout_key");
      router.push(`/orders/${payload.order_id}`);
    } catch {
      setFailure({ code: "network_error", message: t("checkout.failed") });
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="page-split" onSubmit={submit} noValidate>
      <div>
        <section className="panel" aria-labelledby="checkout-contact">
          <h2 id="checkout-contact">{t("checkout.contact")}</h2>
          <div className="form-grid">
            <div className="form-row">
              <label className="field-label" htmlFor="recipient">
                {t("checkout.name")} <span className="req">*</span>
              </label>
              <input
                id="recipient"
                name="recipient_name"
                className={`input ${errors.recipient_name ? "invalid" : ""}`}
                value={form.recipient_name}
                onChange={(event) => set("recipient_name", event.target.value)}
                autoComplete="name"
                aria-invalid={Boolean(errors.recipient_name)}
                aria-describedby={errors.recipient_name ? "recipient-error" : undefined}
              />
              {errors.recipient_name ? (
                <p className="field-error" id="recipient-error" role="alert">
                  {errors.recipient_name}
                </p>
              ) : null}
            </div>

            <div className="form-row two">
              <div className="form-row">
                <label className="field-label" htmlFor="phone">
                  {t("checkout.phone")} <span className="req">*</span>
                </label>
                <input
                  id="phone"
                  name="phone"
                  className={`input ${errors.phone ? "invalid" : ""}`}
                  value={form.phone}
                  onChange={(event) => set("phone", event.target.value)}
                  inputMode="tel"
                  autoComplete="tel"
                  dir="ltr"
                  placeholder="+201000000001"
                  aria-invalid={Boolean(errors.phone)}
                />
                {errors.phone ? (
                  <p className="field-error" role="alert">
                    {errors.phone}
                  </p>
                ) : null}
              </div>
              <div className="form-row">
                <label className="field-label" htmlFor="city">
                  {t("checkout.city")} <span className="req">*</span>
                </label>
                <input
                  id="city"
                  name="city"
                  className={`input ${errors.city ? "invalid" : ""}`}
                  value={form.city}
                  onChange={(event) => set("city", event.target.value)}
                  autoComplete="address-level2"
                  aria-invalid={Boolean(errors.city)}
                />
                {errors.city ? (
                  <p className="field-error" role="alert">
                    {errors.city}
                  </p>
                ) : null}
              </div>
            </div>

            <div className="form-row">
              <label className="field-label" htmlFor="address">
                {t("checkout.address")} <span className="req">*</span>
              </label>
              <textarea
                id="address"
                name="address_line"
                className={`input ${errors.address_line ? "invalid" : ""}`}
                value={form.address_line}
                onChange={(event) => set("address_line", event.target.value)}
                rows={3}
                autoComplete="street-address"
                aria-invalid={Boolean(errors.address_line)}
              />
              {errors.address_line ? (
                <p className="field-error" role="alert">
                  {errors.address_line}
                </p>
              ) : null}
            </div>

            <div className="form-row checkbox-row">
              <input
                id="save-address"
                name="save_address"
                type="checkbox"
                checked={saveAddress}
                onChange={(event) => setSaveAddress(event.target.checked)}
              />
              <label className="field-label" htmlFor="save-address">
                {t("checkout.saveAddress")}
              </label>
              <p className="field-hint">{t("checkout.saveAddressHint")}</p>
            </div>
          </div>
        </section>

        <section className="panel" aria-labelledby="checkout-payment">
          <h2 id="checkout-payment">{t("checkout.payment")}</h2>
          <div className="form-grid">
            <div className="form-row">
              <label className="field-label" htmlFor="payment_token">
                {t("checkout.method")}
              </label>
              <select
                id="payment_token"
                name="payment_token"
                className="input"
                value={form.payment_token}
                onChange={(event) => set("payment_token", event.target.value)}
              >
                {TOKENS.map((token) => (
                  <option value={token.value} key={token.value}>
                    {token.label[locale]}
                  </option>
                ))}
              </select>
              <p className="field-hint">{t("checkout.tokenHint")}</p>
            </div>
          </div>
        </section>
      </div>

      <aside className="summary-aside">
        <div className="panel" aria-labelledby="checkout-review">
        <h2 id="checkout-review">{t("checkout.review")}</h2>
        <ul className="summary-lines">
          {cart.items.map((item) => (
            <li key={item.product_id}>
              <span>
                {names[item.product_id] ?? item.product_id} × {item.quantity}
              </span>
              <span className="price-amount">
                {formatMoney(multiplyMoney(item.unit_price, item.quantity), locale)} {cart.currency}
              </span>
            </li>
          ))}
        </ul>
        <div className="totals" style={{ marginBlockStart: 12 }}>
          <div className="grand">
            <span>{t("checkout.total")}</span>
            <span>
              {formatMoney(subtotal, locale)} {cart.currency}
            </span>
          </div>
        </div>

        {failure ? (
          <div className="notice" data-tone="error" role="alert" style={{ marginBlockStart: 12 }}>
            <div>
              <strong>{t("checkout.failed")}</strong>
              <p style={{ margin: 0 }}>{failure.message}</p>
              {failure.code ? <p style={{ margin: 0 }}>code: {failure.code}</p> : null}
            </div>
          </div>
        ) : null}

        <button
          type="submit"
          className="btn btn-primary btn-block"
          style={{ marginBlockStart: 14 }}
          disabled={busy}
          aria-busy={busy}
        >
          {busy ? t("checkout.submitting") : t("checkout.submit")}
        </button>
        <p className="field-hint" style={{ marginBlockStart: 8 }}>
          {t("checkout.riskNote")}
        </p>
        </div>
      </aside>
    </form>
  );
}