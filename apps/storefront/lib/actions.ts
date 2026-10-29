import Link from "next/link";
import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";
import { LOCALE_COOKIE } from "@/lib/locale";

export async function switchLocale(formData: FormData) {
  "use server";
  const target = formData.get("locale") === "en" ? "en" : "ar";
  const store = await cookies();
  store.set(LOCALE_COOKIE, target, {
    path: "/",
    maxAge: 60 * 60 * 24 * 365,
    sameSite: "lax",
  });
  const referer = (await headers()).get("referer");
  let destination = "/";
  if (referer) {
    try {
      const url = new URL(referer);
      destination = `${url.pathname}${url.search}`;
    } catch {
      destination = "/";
    }
  }
  redirect(destination);
}