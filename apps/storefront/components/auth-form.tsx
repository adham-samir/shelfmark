"use client";

import Link from "next/link";
import { useActionState } from "react";
import type { Locale } from "@/lib/types";
import { translator } from "@/lib/i18n";
import { initialAuthFormState } from "@/lib/action-states";
import { registerAccount, signIn } from "@/lib/auth-actions";

type Mode = "login" | "register" | "operator";

export function AuthForm({
  locale,
  mode,
  next,
}: {
  locale: Locale;
  mode: Mode;
  next: string;
}) {
  const t = translator(locale);
  const registering = mode === "register";
  const [state, action, pending] = useActionState(
    registering ? registerAccount : signIn,
    initialAuthFormState,
  );

  const failure =
    state.code === "invalid_credentials"
      ? t("auth.invalid")
      : state.code === "rate_limited"
        ? t("auth.rateLimited")
        : state.code === "conflict"
          ? t("auth.conflict")
          : state.code === "invalid_input"
            ? t("auth.invalidInput")
            : state.code === "dependency_unavailable"
              ? t("auth.unavailable")
              : t("auth.unknown");

  return (
    <div className="auth-grid">
      <form className="panel auth-form" action={action} noValidate>
        {mode === "operator" ? <input type="hidden" name="surface" value="operator" /> : null}
        <input type="hidden" name="next" value={next} />
        {registering ? <input type="hidden" name="locale" value={locale} /> : null}

        <div className="form-row">
          <label className="field-label" htmlFor="auth-email">
            {t("auth.email")} <span className="req">*</span>
          </label>
          <input
            id="auth-email"
            className="input"
            name="email"
            type="email"
            dir="ltr"
            autoComplete="email"
            required
            placeholder={mode === "operator" ? "operator@example.invalid" : "customer@example.invalid"}
          />
        </div>

        {registering ? (
          <div className="form-row">
            <label className="field-label" htmlFor="auth-name">
              {t("auth.displayName")} <span className="req">*</span>
            </label>
            <input
              id="auth-name"
              className="input"
              name="display_name"
              autoComplete="name"
              minLength={2}
              maxLength={120}
              required
            />
          </div>
        ) : null}

        <div className="form-row">
          <label className="field-label" htmlFor="auth-password">
            {t("auth.password")} <span className="req">*</span>
          </label>
          <input
            id="auth-password"
            className="input"
            name="password"
            type="password"
            dir="ltr"
            autoComplete={registering ? "new-password" : "current-password"}
            minLength={registering ? 8 : 1}
            maxLength={128}
            required
          />
        </div>

        {registering ? (
          <div className="form-row">
            <label className="field-label" htmlFor="auth-password-confirm">
              {t("auth.passwordConfirm")} <span className="req">*</span>
            </label>
            <input
              id="auth-password-confirm"
              className="input"
              name="password_confirm"
              type="password"
              dir="ltr"
              autoComplete="new-password"
              minLength={8}
              maxLength={128}
              required
            />
          </div>
        ) : null}

        <div className="form-actions">
          <button className="btn btn-primary" type="submit" disabled={pending}>
            {registering ? t("auth.registerSubmit") : t("auth.submit")}
          </button>
          {state.kind === "error" ? (
            <p className="field-error" role="alert">
              {failure}
            </p>
          ) : null}
        </div>

        <p className="auth-switch">
          {registering ? (
            <>
              {t("auth.haveAccount")}{" "}
              <Link href={`/login?next=${encodeURIComponent(next)}`}>{t("auth.goLogin")}</Link>
            </>
          ) : mode === "login" ? (
            <>
              {t("auth.noAccount")}{" "}
              <Link href={`/register?next=${encodeURIComponent(next)}`}>{t("auth.goRegister")}</Link>
            </>
          ) : (
            <Link href="/login">{t("auth.goLogin")}</Link>
          )}
        </p>
      </form>

      <aside className="panel auth-demo" aria-labelledby="demo-accounts">
        <h2 id="demo-accounts">{t("auth.demoTitle")}</h2>
        <p className="field-hint">{t("auth.demoNote")}</p>
        <ul>
          <li dir="ltr">{t("auth.demoCustomer")}</li>
          <li dir="ltr">{t("auth.demoOther")}</li>
          <li dir="ltr">{t("auth.demoOperator")}</li>
        </ul>
        {mode === "operator" ? <p className="field-hint">{t("admin.operatorOnly")}</p> : null}
      </aside>
    </div>
  );
}
