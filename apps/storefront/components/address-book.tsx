"use client";

import { useActionState, useState } from "react";
import type { Address, Locale } from "@/lib/types";
import { translator } from "@/lib/i18n";
import { initialAddressFormState } from "@/lib/action-states";
import { createAddress, deleteAddress, updateAddress } from "@/lib/address-actions";

function failureMessage(
  t: ReturnType<typeof translator>,
  code: string | undefined,
): string {
  switch (code) {
    case "conflict":
      return t("addresses.conflict");
    case "not_found":
      return t("addresses.missing");
    case "invalid_input":
      return t("addresses.invalid");
    case "forbidden":
    case "unauthorized":
      return t("addresses.unauthorized");
    default:
      return t("addresses.failed");
  }
}

export function AddressForm({ locale }: { locale: Locale }) {
  const t = translator(locale);
  const [state, action, pending] = useActionState(
    createAddress,
    initialAddressFormState,
  );

  return (
    <form className="panel" action={action} noValidate>
      <h2>{t("addresses.add")}</h2>
      <div className="form-grid" style={{ marginBlockStart: 12 }}>
        <div className="form-row two">
          <div className="form-row">
            <label className="field-label" htmlFor="address-label">
              {t("addresses.label")} <span className="req">*</span>
            </label>
            <input
              className="input"
              id="address-label"
              name="label"
              required
              minLength={1}
              maxLength={60}
              placeholder={t("addresses.labelPlaceholder")}
            />
          </div>
          <div className="form-row">
            <label className="field-label" htmlFor="address-name">
              {t("addresses.recipient")} <span className="req">*</span>
            </label>
            <input
              className="input"
              id="address-name"
              name="recipient_name"
              required
              minLength={2}
              maxLength={120}
              autoComplete="name"
            />
          </div>
        </div>
        <div className="form-row two">
          <div className="form-row">
            <label className="field-label" htmlFor="address-phone">
              {t("addresses.phone")} <span className="req">*</span>
            </label>
            <input
              className="input"
              id="address-phone"
              name="phone"
              required
              dir="ltr"
              inputMode="tel"
              autoComplete="tel"
              placeholder="+201000000001"
            />
          </div>
          <div className="form-row">
            <label className="field-label" htmlFor="address-city">
              {t("addresses.city")} <span className="req">*</span>
            </label>
            <input
              className="input"
              id="address-city"
              name="city"
              required
              minLength={2}
              maxLength={80}
              autoComplete="address-level2"
            />
          </div>
        </div>
        <div className="form-row">
          <label className="field-label" htmlFor="address-line">
            {t("addresses.line")} <span className="req">*</span>
          </label>
          <textarea
            className="input"
            id="address-line"
            name="address_line"
            required
            minLength={5}
            maxLength={300}
            rows={3}
            autoComplete="street-address"
          />
        </div>
        <div className="form-row checkbox-row">
          <input id="address-default" name="is_default" type="checkbox" />
          <label className="field-label" htmlFor="address-default">
            {t("addresses.makeDefault")}
          </label>
        </div>
      </div>
      <div className="row-actions" style={{ marginBlockStart: 12 }}>
        <button className="btn btn-dark" type="submit" disabled={pending}>
          {pending ? t("addresses.saving") : t("addresses.save")}
        </button>
      </div>
      <p aria-live="polite" data-tone={state.kind}>
        {state.kind === "success"
          ? t("addresses.created")
          : state.kind === "error"
            ? failureMessage(t, state.code)
            : null}
      </p>
    </form>
  );
}

export function AddressCard({
  locale,
  address,
}: {
  locale: Locale;
  address: Address;
}) {
  const t = translator(locale);
  const [editing, setEditing] = useState(false);
  const [updateState, updateAction, updating] = useActionState(
    updateAddress,
    initialAddressFormState,
  );
  const [deleteState, deleteAction, deleting] = useActionState(
    deleteAddress,
    initialAddressFormState,
  );

  if (editing) {
    return (
      <section className="panel" aria-label={address.label}>
        <h2>{t("addresses.edit")}</h2>
        <form action={updateAction} className="form-grid" style={{ marginBlockStart: 12 }}>
          <input type="hidden" name="address_id" value={address.address_id} />
          <div className="form-row two">
            <div className="form-row">
              <label className="field-label" htmlFor={`label-${address.address_id}`}>
                {t("addresses.label")} <span className="req">*</span>
              </label>
              <input
                className="input"
                id={`label-${address.address_id}`}
                name="label"
                defaultValue={address.label}
                required
                maxLength={60}
              />
            </div>
            <div className="form-row">
              <label className="field-label" htmlFor={`name-${address.address_id}`}>
                {t("addresses.recipient")} <span className="req">*</span>
              </label>
              <input
                className="input"
                id={`name-${address.address_id}`}
                name="recipient_name"
                defaultValue={address.recipient_name}
                required
                minLength={2}
                maxLength={120}
              />
            </div>
          </div>
          <div className="form-row two">
            <div className="form-row">
              <label className="field-label" htmlFor={`phone-${address.address_id}`}>
                {t("addresses.phone")} <span className="req">*</span>
              </label>
              <input
                className="input"
                id={`phone-${address.address_id}`}
                name="phone"
                defaultValue={address.phone}
                required
                dir="ltr"
                inputMode="tel"
              />
            </div>
            <div className="form-row">
              <label className="field-label" htmlFor={`city-${address.address_id}`}>
                {t("addresses.city")} <span className="req">*</span>
              </label>
              <input
                className="input"
                id={`city-${address.address_id}`}
                name="city"
                defaultValue={address.city}
                required
                minLength={2}
                maxLength={80}
              />
            </div>
          </div>
          <div className="form-row">
            <label className="field-label" htmlFor={`line-${address.address_id}`}>
              {t("addresses.line")} <span className="req">*</span>
            </label>
            <textarea
              className="input"
              id={`line-${address.address_id}`}
              name="address_line"
              defaultValue={address.address_line}
              required
              minLength={5}
              maxLength={300}
              rows={3}
            />
          </div>
          <div className="form-row checkbox-row">
            <input
              id={`default-${address.address_id}`}
              name="is_default"
              type="checkbox"
              defaultChecked={address.is_default}
            />
            <label className="field-label" htmlFor={`default-${address.address_id}`}>
              {t("addresses.makeDefault")}
            </label>
          </div>
          <div className="row-actions">
            <button className="btn btn-dark" type="submit" disabled={updating}>
              {updating ? t("addresses.saving") : t("addresses.saveChanges")}
            </button>
            <button
              className="btn btn-quiet"
              type="button"
              onClick={() => setEditing(false)}
            >
              {t("common.back")}
            </button>
          </div>
          <p aria-live="polite" data-tone={updateState.kind}>
            {updateState.kind === "success"
              ? t("addresses.updated")
              : updateState.kind === "error"
                ? failureMessage(t, updateState.code)
                : null}
          </p>
        </form>
      </section>
    );
  }

  return (
    <section className="panel" aria-label={address.label}>
      <div className="row-actions" style={{ justifyContent: "space-between" }}>
        <h2>
          {address.label}
          {address.is_default ? (
            <span className="pill" data-status="confirmed" style={{ marginInlineStart: 8 }}>
              {t("addresses.default")}
            </span>
          ) : null}
        </h2>
      </div>
      <dl className="detail-specs" style={{ marginBlockStart: 10 }}>
        <div>
          <dt>{t("addresses.recipient")}</dt>
          <dd>{address.recipient_name}</dd>
        </div>
        <div>
          <dt>{t("addresses.phone")}</dt>
          <dd dir="ltr">{address.phone}</dd>
        </div>
        <div>
          <dt>{t("addresses.city")}</dt>
          <dd>{address.city}</dd>
        </div>
        <div>
          <dt>{t("addresses.line")}</dt>
          <dd>{address.address_line}</dd>
        </div>
      </dl>
      <div className="row-actions" style={{ marginBlockStart: 12 }}>
        <button className="btn btn-quiet" type="button" onClick={() => setEditing(true)}>
          {t("addresses.edit")}
        </button>
        <form action={deleteAction}>
          <input type="hidden" name="address_id" value={address.address_id} />
          <button className="btn btn-quiet" type="submit" disabled={deleting}>
            {deleting ? t("addresses.deleting") : t("addresses.delete")}
          </button>
        </form>
      </div>
      <p aria-live="polite" data-tone={deleteState.kind}>
        {deleteState.kind === "success"
          ? t("addresses.deleted")
          : deleteState.kind === "error"
            ? failureMessage(t, deleteState.code)
            : null}
      </p>
    </section>
  );
}
