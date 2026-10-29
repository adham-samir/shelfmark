import { cache } from "react";
import { api } from "./api";

/**
 * Per-request memoised reads. Metadata and the page body resolve the same
 * entity once, so a missing record can be turned into a real 404 before the
 * response starts streaming.
 */
export const getProduct = cache((productId: string) => api.product(productId));
export const getOrder = cache((orderId: string) => api.order(orderId));
