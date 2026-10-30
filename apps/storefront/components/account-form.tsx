"use client";

import { useActionState } from "react";
import type { AccountProfile, Locale } from "@/lib/types";
import { translator } from "@/lib/i18n";
import { initialAccountFormState } from "@/lib/action-states";
import { saveAccount } from "@/lib/auth-actions";

export function AccountForm({
  locale,
  profile,
}: {
  locale: Locale;
  profile: AccountProfile;
}) {
  const t = translator(locale);
  const [state, action, pending] = useActionState(saveAccount, initialAccountFormState);

  return (
    <form className="panel" action={action} noValidate>
      <h2>{t("account.profile")}</h2>
      <div className="form-grid">
        <div className="form-row">
          <label className="field-label" htmlFor="account-name">
            {t("account.name")} <span className="req">*</span>
          </label>
          <input
            id="account-name"
            className="input"
            name="display_name"
            defaultValue={profile.display_name}
            minLength={2}
            maxLength={120}
            autoComplete="name"
            required
          />
        </div>

        <div className="form-row">
          <label className="field-label" htmlFor="account-email">
            {t("account.email")}
          </label>
          <input
            id="account-email"
            className="input"
            value={profile.email}
            dir="ltr"
            readOnly
            aria-describedby="account-email-hint"
          />
          <p className="field-hint" id="account-email-hint" dir="ltr">
            {profile.email}
          </p>
        </div>

        <div className="form-row">
          <label className="field-label" htmlFor="account-locale">
            {t("account.locale")}
          </label>
          <select
            id="account-locale"
            className="input"
            name="preferred_locale"
            defaultValue={profile.preferred_locale}
          >
            <option value="ar">{t("account.localeAr")}</option>
            <option value="en">{t("account.localeEn")}</option>
          </select>
        </div>

        <div className="form-actions">
          <button className="btn btn-primary" type="submit" disabled={pending}>
            {t("account.save")}
          </button>
          <p aria-live="polite" data-tone={state.kind}>
            {state.kind === "success"
              ? t("account.saved")
              : state.kind === "error"
                ? state.code === "invalid_input"
                  ? t("account.invalid")
                  : state.code === "unauthorized"
                    ? t("auth.invalid")
                    : t("account.failed")
                : null}
          </p>
        </div>
      </div>
    </form>
  );
}
