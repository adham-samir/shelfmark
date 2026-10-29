import type { Product } from "./types";

/**
 * Demonstration imagery.
 *
 * The catalog fixtures intentionally carry no remote image URIs: the API's
 * Image contract only accepts https URLs and this project has no licensed
 * product photography or CDN. Four base raster plates and two synthetic
 * angle/tone variants per base were generated for the synthetic fixtures
 * (prompts in `.impeccable/build/prompts/`)
 * and are mapped to fixture IDs so that neighbouring cards do not present the
 * same photograph as different products. Every card carries the "synthetic product" label.
 *
 * Provenance: generated for this repository, demonstration use only.
 */
const PLATES: Record<string, { src: string; alt: string }> = {
  "10000000-0000-4000-8000-000000000001": {
    src: "/products/phone-blue.png",
    alt: "Synthetic blue smartphone, X1 demonstration image",
  },
  "10000000-0000-4000-8000-000000000002": {
    src: "/products/phone-red.png",
    alt: "Synthetic red smartphone, Y2 demonstration image",
  },
  "10000000-0000-4000-8000-000000000003": {
    src: "/products/headphones-black.png",
    alt: "Synthetic over-ear headphones, H1 demonstration image",
  },
  "10000000-0000-4000-8000-000000000004": {
    src: "/products/laptop-silver.png",
    alt: "Synthetic silver laptop, L1 demonstration image",
  },
  "10000000-0000-4000-8000-000000000005": {
    src: "/products/phone-blue-alt1.png",
    alt: "Synthetic blue smartphone, X2 demonstration image",
  },
  "10000000-0000-4000-8000-000000000006": {
    src: "/products/phone-red-alt1.png",
    alt: "Synthetic red smartphone, Z3 demonstration image",
  },
  "10000000-0000-4000-8000-000000000007": {
    src: "/products/phone-blue-alt2.png",
    alt: "Synthetic blue smartphone, Q4 demonstration image",
  },
  "10000000-0000-4000-8000-000000000008": {
    src: "/products/headphones-black-alt1.png",
    alt: "Synthetic over-ear headphones, H2 demonstration image",
  },
  "10000000-0000-4000-8000-000000000009": {
    src: "/products/headphones-black-alt2.png",
    alt: "Synthetic in-ear headphones, H3 demonstration image",
  },
  "10000000-0000-4000-8000-000000000010": {
    src: "/products/headphones-black-alt1.png",
    alt: "Synthetic wired headphones, H4 demonstration image",
  },
  "10000000-0000-4000-8000-000000000011": {
    src: "/products/laptop-silver-alt1.png",
    alt: "Synthetic silver laptop, L2 demonstration image",
  },
  "10000000-0000-4000-8000-000000000012": {
    src: "/products/laptop-silver-alt2.png",
    alt: "Synthetic silver laptop, L3 demonstration image",
  },
  "10000000-0000-4000-8000-000000000013": {
    src: "/products/laptop-silver-alt1.png",
    alt: "Synthetic silver laptop, L4 demonstration image",
  },
};

export function plateFor(product: Pick<Product, "product_id" | "name">): {
  src: string;
  alt: string;
} | null {
  return PLATES[product.product_id] ?? null;
}

export function monogram(product: Pick<Product, "name">): string {
  return product.name.trim().slice(0, 2).toUpperCase();
}