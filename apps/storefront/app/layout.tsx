import type { Metadata } from "next";
import { Alexandria } from "next/font/google";
import "./globals.css";
import { direction, getLocale } from "@/lib/locale";

const alexandria = Alexandria({
  subsets: ["arabic", "latin"],
  weight: ["400", "500", "600"],
  display: "swap",
  variable: "--font-alexandria",
});

export const metadata: Metadata = {
  title: "Smart-eCommerce Management System",
  description:
    "Synthetic bilingual smart-commerce demonstration: customer storefront and operator back office.",
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
