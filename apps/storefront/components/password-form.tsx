"use client";

import { useActionState } from "react";
import type { Locale } from "@/lib/types";
import { translator } from "@/lib/i18n";
import { initialPasswordFormState } from "@/lib/action-states";
import { changePassword } from "@/lib/auth-actions";

export function PasswordForm({ locale }: { locale: Locale }) {
  const t = translator(locale);
  const [state, action, pending] = useActionState(
    changePassword,
    initialPasswordFormState,
  );

  const failure =
    state.code === "wrong_password"
      ? t("account.passwordWrong")
      : state.code === "invalid_input"
        ? t("account.passwordInvalid")
        : state.code === "unauthorized"
          ? t("account.passwordExpired")
          : t("account.passwordFailed");

  return (
    <form className="panel" action={action} noValidate>
      <h2>{t("account.security")}</h2>
      <p className="field-hint">{t("account.passwordHint")}</p>
      <div className="form-grid" style={{ marginBlockStart: 12 }}>
        <div className="form-row">
          <label className="field-label" htmlFor="current-password">
            {t("account.currentPassword")} <span className="req">*</span>
          </label>
          <input
            id="current-password"
            className="input"
            name="current_password"
            type="password"
            autoComplete="current-password"
            minLength={1}
            maxLength={128}
            required
          />
        </div>
        <div className="form-row two">
          <div className="form-row">
            <label className="field-label" htmlFor="new-password">
              {t("account.newPassword")} <span className="req">*</span>
            </label>
            <input
              id="new-password"
              className="input"
              name="new_password"
              type="password"
              autoComplete="new-password"
              minLength={8}
              maxLength={128}
              required
            />
          </div>
          <div className="form-row">
            <label className="field-label" htmlFor="confirm-password">
              {t("account.confirmPassword")} <span className="req">*</span>
            </label>
            <input
              id="confirm-password"
              className="input"
              name="confirm_password"
              type="password"
              autoComplete="new-password"
              minLength={8}
              maxLength={128}
              required
            />
          </div>
        </div>
      </div>
      <div className="row-actions" style={{ marginBlockStart: 12 }}>
        <button className="btn btn-dark" type="submit" disabled={pending}>
          {pending ? t("account.passwordSaving") : t("account.passwordSubmit")}
        </button>
      </div>
      <p aria-live="polite" data-tone={state.kind}>
        {state.kind === "success"
          ? t("account.passwordSaved", { count: state.revoked ?? 0 })
          : state.kind === "error"
            ? failure
            : null}
      </p>
    </form>
  );
}
