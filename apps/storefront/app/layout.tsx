import type { Metadata } from "next";
import { Alexandria } from "next/font/google";
import "./globals.css";
import { direction, getLocale } from "@/lib/locale";
import { SITE_DESCRIPTION, SITE_NAME, SITE_TITLE_TEMPLATE } from "@/lib/site";

const alexandria = Alexandria({
  subsets: ["arabic", "latin"],
  weight: ["400", "500", "600"],
  display: "swap",
  variable: "--font-alexandria",
});

export const metadata: Metadata = {
  title: {
    default: SITE_NAME,
    template: SITE_TITLE_TEMPLATE,
  },
  description: SITE_DESCRIPTION,
};

export default async function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const locale = await getLocale();
  return (
    <html lang={locale} dir={direction(locale)} className={alexandria.variable}>
      <body>{children}</body>
    </html>
  );
}
