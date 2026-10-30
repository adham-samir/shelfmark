import type { Metadata } from "next";
import Link from "next/link";
import type {
  InventoryPlanningResponse,
  Locale,
  PricingOverviewResponse,
  ReviewQueueItem,
  SegmentationResponse,
} from "@/lib/types";
import { api } from "@/lib/api";
import { getLocale } from "@/lib/locale";
import { translator } from "@/lib/i18n";
import { formatDate } from "@/lib/format";
import { Notice } from "@/components/states";

export const metadata: Metadata = { title: "لوحة الإدارة — Smart-eCommerce" };

export default async function BackofficeHomePage() {
  const locale: Locale = await getLocale();
  const t = translator(locale);

  const [reviews, pricing, inventory, segments] = await Promise.allSettled([
    api.riskReviews(),
    api.pricing(),
    api.inventory(),
    api.segments({ limit: 1 }),
  ]);

  const reviewCount =
    reviews.status === "fulfilled" ? (reviews.value as ReviewQueueItem[]).length : null;
  const stalePricing =
    pricing.status === "fulfilled"
      ? (pricing.value as PricingOverviewResponse).items.filter(
          (item) => item.input_status !== "fresh",
        ).length
      : null;
  const reorderFailures =
    inventory.status === "fulfilled"
      ? (inventory.value as InventoryPlanningResponse).items.filter(
          (item) => item.planning_status === "supplier_failed",
        ).length
      : null;
  const snapshot =
    segments.status === "fulfilled"
      ? (segments.value as SegmentationResponse).reference_date
      : null;

  const cards = [
    {
      href: "/backoffice/risk",
      title: t("admin.pendingReviews"),
      value: reviewCount,
    },
    {
      href: "/backoffice/pricing",
      title: t("admin.stalePricing"),
      value: stalePricing,
    },
    {
      href: "/backoffice/inventory",
      title: t("admin.reorderFailures"),
      value: reorderFailures,
    },
    {
      href: "/backoffice/segments",
      title: t("admin.snapshotAge"),
      value: snapshot,
    },
  ];

  return (
    <main className="page bo-home" id="main">
      <div className="page-head">
        <div>
          <p className="eyebrow">{t("nav.backoffice")}</p>
          <h1>{t("admin.dashboard")}</h1>
          <p>{t("admin.operatorOnly")}</p>
        </div>
      </div>

      <div className="bo-cards anim">
        {cards.map((card, index) => (
          <section
            className="panel bo-card"
            key={card.href}
            style={{ "--i": index } as React.CSSProperties}
          >
            <h2>{card.title}</h2>
            <p className="bo-card-value">
              {card.value === null
                ? "—"
                : typeof card.value === "string"
                  ? formatDate(card.value, locale)
                  : card.value}
            </p>
            <Link className="btn btn-quiet" href={card.href}>
              {t("admin.open")}
            </Link>
          </section>
        ))}
      </div>

      <div style={{ marginBlockStart: 18 }}>
        <Notice tone="info">{t("admin.gateHint")}</Notice>
      </div>
    </main>
  );
}
