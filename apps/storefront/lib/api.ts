/**
 * Server-side client for the FastAPI service.
 *
 * The storefront talks to the API only from the Next.js server (server
 * components, server actions and route handlers), so the synthetic sandbox
 * bearer value never reaches the browser. Production identity remains an
 * explicit open decision (docs/decisions.md); this adapter is demonstration
 * plumbing, not an authentication implementation.
 */
import type {
  Address,
  AddressList,
  AccountProfile,
  AccountView,
  AssistantResponse,
  AuthSession,
  Cart,
  CatalogFacets,
  ImageSearchResponse,
  Order,
  OrderAdjustmentResult,
  OrderList,
  OrderState,
  OrderStatus,
  InventoryAdjustmentResult,
  OperatorOrderDetail,
  OperatorOrderList,
  Product,
  ProductPage,
  RecommendationResult,
  ReorderResult,
  Shipment,
  VoiceSearchResponse,
  InventoryPlanningResponse,
  ReorderRunResult,
  PricingObservationResult,
  PricingOverviewResponse,
  PricingRunResult,
  AnalyticsResponse,
  FraudModelSummary,
  ReviewDecisionResult,
  ReviewQueueItem,
  RfmPolicy,
  SegmentationResponse,
  SegmentationRunResult,
} from "./types";
import { readSessionToken } from "./session-cookie";

const API_BASE_URL = process.env.SMART_ECOMMERCE_API_URL ?? "http://127.0.0.1:8000";

export type ApiErrorCode =
  | "dependency_unavailable"
  | "unauthorized"
  | "forbidden"
  | "not_found"
  | "conflict"
  | "invalid_input"
  | "incorrect_password"
  | "network_error"
  | "unknown";

export class ApiError extends Error {
  readonly code: ApiErrorCode;
  readonly status: number;
  readonly requestId?: string;

  constructor(code: ApiErrorCode, status: number, message: string, requestId?: string) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.requestId = requestId;
  }
}

interface ApiErrorBody {
  error?: { code?: string; message?: string; request_id?: string };
}

function errorCode(code: string | undefined, status: number): ApiErrorCode {
  switch (code) {
    case "dependency_unavailable":
    case "unauthorized":
    case "forbidden":
    case "product_not_found":
      return code === "product_not_found" ? "not_found" : code;
    case "conflict":
    case "invalid_input":
    case "incorrect_password":
      return code;
    default:
      if (status === 401) return "unauthorized";
      if (status === 403) return "forbidden";
      if (status === 404) return "not_found";
      if (status === 409) return "conflict";
      if (status === 422) return "invalid_input";
      if (status === 503) return "dependency_unavailable";
      return "unknown";
  }
}

export interface ApiRequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  formData?: FormData;
  /** Kept for call-site clarity: all API reads are uncached. */
  noStore?: boolean;
  headers?: Record<string, string>;
  signal?: AbortSignal;
  /**
   * Which server-side session to attach. Public catalog reads use "none";
   * customer and operator calls read the matching httpOnly cookie.
   */
  auth?: "customer" | "operator" | "none";
}

export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const auth = options.auth ?? "none";
  const headers: Record<string, string> = {
    accept: "application/json",
    ...options.headers,
  };
  if (auth !== "none") {
    const token = await readSessionToken(auth);
    if (!token) {
      throw new ApiError("unauthorized", 401, "Sign in to continue.");
    }
    headers.authorization = `Bearer ${token}`;
  }
  let body: BodyInit | undefined;
  if (options.formData) {
    body = options.formData;
  } else if (options.body !== undefined) {
    headers["content-type"] = "application/json";
    body = JSON.stringify(options.body);
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: options.method ?? "GET",
      headers,
      body,
      // Catalog price and availability are authoritative reads: never serve a
      // stale cached copy. Every call hits the API service.
      cache: "no-store",
      signal: options.signal,
    });
  } catch (error) {
    throw new ApiError(
      "network_error",
      0,
      error instanceof Error ? error.message : "The API service is unreachable.",
    );
  }

  if (!response.ok) {
    let payload: ApiErrorBody = {};
    try {
      payload = (await response.json()) as ApiErrorBody;
    } catch {
      /* the API may answer with an empty body on infrastructure failures */
    }
    const code = errorCode(payload.error?.code, response.status);
    throw new ApiError(
      code,
      response.status,
      payload.error?.message ?? `The API answered ${response.status}.`,
      payload.error?.request_id,
    );
  }

  if (response.status === 204 || response.status === 202) {
    const text = await response.text();
    return (text ? JSON.parse(text) : ({} as T)) as T;
  }
  return (await response.json()) as T;
}

export interface CatalogQuery {
  q?: string;
  category?: string;
  filters?: Record<string, string>;
  availability?: "in_stock" | "out_of_stock";
  sort?: "relevance" | "price_asc" | "price_desc" | "name_asc";
  priceMin?: string;
  priceMax?: string;
  limit?: number;
  offset?: number;
}

export function catalogSearchParams(query: CatalogQuery): URLSearchParams {
  const params = new URLSearchParams();
  if (query.q) params.set("q", query.q);
  if (query.category) params.set("category", query.category);
  if (query.availability) params.set("availability", query.availability);
  if (query.sort && query.sort !== "relevance") params.set("sort", query.sort);
  if (query.priceMin) params.set("price_min", query.priceMin);
  if (query.priceMax) params.set("price_max", query.priceMax);
  if (query.limit) params.set("limit", String(query.limit));
  if (query.offset) params.set("offset", String(query.offset));
  for (const [key, value] of Object.entries(query.filters ?? {})) {
    params.append("filter", `${key}:${value}`);
  }
  return params;
}

export const api = {
  products(query: CatalogQuery = {}): Promise<ProductPage> {
    return apiRequest<ProductPage>(`/v1/products?${catalogSearchParams(query)}`);
  },
  facets(query: Omit<CatalogQuery, "limit" | "offset" | "sort"> = {}): Promise<CatalogFacets> {
    return apiRequest<CatalogFacets>(`/v1/products/facets?${catalogSearchParams(query)}`);
  },
  product(productId: string): Promise<Product> {
    return apiRequest<Product>(`/v1/products/${productId}`);
  },
  recommendations(limit = 4): Promise<RecommendationResult> {
    return apiRequest<RecommendationResult>(`/v1/recommendations?limit=${limit}`, {
      auth: "customer",
      noStore: true,
    });
  },
  cart(): Promise<Cart> {
    return apiRequest<Cart>("/v1/cart", { auth: "customer", noStore: true });
  },
  setCartItem(productId: string, quantity: number): Promise<Cart> {
    return apiRequest<Cart>("/v1/cart/items", {
      method: "PUT",
      body: { product_id: productId, quantity },
      auth: "customer",
      noStore: true,
    });
  },
  checkout(input: {
    payment_token: string;
    idempotency_key: string;
    shipping: {
      recipient_name: string;
      phone: string;
      city: string;
      address_line: string;
    };
  }): Promise<OrderStatus> {
    return apiRequest<OrderStatus>("/v1/checkout", {
      method: "POST",
      body: input,
      auth: "customer",
      noStore: true,
    });
  },
  order(orderId: string): Promise<Order> {
    return apiRequest<Order>(`/v1/orders/${orderId}`, {
      auth: "customer",
      noStore: true,
    });
  },
  orders(params: { limit?: number; offset?: number } = {}): Promise<OrderList> {
    const search = new URLSearchParams();
    if (params.limit) search.set("limit", String(params.limit));
    if (params.offset) search.set("offset", String(params.offset));
    return apiRequest<OrderList>(`/v1/orders?${search}`, {
      auth: "customer",
      noStore: true,
    });
  },
  shipment(orderId: string): Promise<Shipment> {
    return apiRequest<Shipment>(`/v1/orders/${orderId}/shipment`, {
      auth: "customer",
      noStore: true,
    });
  },
  assistant(input: {
    message: string;
    locale: "ar" | "en";
    order_id?: string;
  }): Promise<AssistantResponse> {
    return apiRequest<AssistantResponse>("/v1/assistant/messages", {
      method: "POST",
      body: input,
      auth: "customer",
      noStore: true,
    });
  },
  imageSearch(formData: FormData, query: CatalogQuery = {}): Promise<ImageSearchResponse> {
    const params = catalogSearchParams({
      category: query.category,
      filters: query.filters,
      limit: query.limit,
    });
    return apiRequest<ImageSearchResponse>(`/v1/search/image?${params}`, {
      method: "POST",
      formData,
      noStore: true,
    });
  },
  voiceSearch(
    formData: FormData,
    locale: "ar" | "en",
    query: CatalogQuery = {},
  ): Promise<VoiceSearchResponse> {
    const params = catalogSearchParams({
      category: query.category,
      filters: query.filters,
      limit: query.limit,
    });
    params.set("locale", locale);
    return apiRequest<VoiceSearchResponse>(`/v1/search/voice?${params}`, {
      method: "POST",
      formData,
      noStore: true,
    });
  },
  recordEvent(input: {
    event_id: string;
    session_id: string;
    product_id: string;
    event_type: "view" | "search_click" | "compare" | "add_to_cart";
    occurred_at: string;
    context?: Record<string, unknown>;
  }): Promise<void> {
    return apiRequest<void>("/v1/events/browsing", {
      method: "POST",
      body: input,
      auth: "customer",
      noStore: true,
    });
  },
  inventory(): Promise<InventoryPlanningResponse> {
    return apiRequest<InventoryPlanningResponse>("/v1/backoffice/inventory", {
      auth: "operator",
      noStore: true,
    });
  },
  runInventoryPlanning(): Promise<ReorderRunResult> {
    return apiRequest<ReorderRunResult>("/v1/backoffice/reorders/run", {
      method: "POST",
      auth: "operator",
      noStore: true,
    });
  },
  pricing(): Promise<PricingOverviewResponse> {
    return apiRequest<PricingOverviewResponse>("/v1/backoffice/pricing", {
      auth: "operator",
      noStore: true,
    });
  },
  runPricing(productIds?: string[]): Promise<PricingRunResult> {
    return apiRequest<PricingRunResult>("/v1/backoffice/pricing/run", {
      method: "POST",
      body: productIds?.length ? { product_ids: productIds } : undefined,
      auth: "operator",
      noStore: true,
    });
  },
  recordPricingObservation(input: {
    product_id: string;
    recorded_cost: string;
    supply: string;
    demand: string;
    competitor_cost: string;
  }): Promise<PricingObservationResult> {
    return apiRequest<PricingObservationResult>("/v1/backoffice/pricing/observations", {
      method: "POST",
      body: { ...input, provenance: "synthetic" },
      auth: "operator",
      noStore: true,
    });
  },
  segments(
    params: {
      segment?: string;
      limit?: number;
      offset?: number;
      referenceDate?: string;
    } = {},
  ): Promise<SegmentationResponse> {
    const search = new URLSearchParams();
    if (params.segment) search.set("segment", params.segment);
    if (params.referenceDate) search.set("reference_date", params.referenceDate);
    if (params.limit) search.set("limit", String(params.limit));
    if (params.offset) search.set("offset", String(params.offset));
    return apiRequest<SegmentationResponse>(
      `/v1/backoffice/segments?${search}`,
      { auth: "operator", noStore: true },
    );
  },
  analytics(params: {
    from: string;
    to: string;
    category?: string;
  }): Promise<AnalyticsResponse> {
    const search = new URLSearchParams({ from: params.from, to: params.to });
    if (params.category) search.set("category", params.category);
    return apiRequest<AnalyticsResponse>(
      `/v1/backoffice/analytics?${search}`,
      { auth: "operator", noStore: true },
    );
  },
  riskReviews(): Promise<ReviewQueueItem[]> {
    return apiRequest<ReviewQueueItem[]>("/v1/backoffice/risk", {
      auth: "operator",
      noStore: true,
    });
  },
  operatorOrders(
    params: { status?: OrderState; limit?: number; offset?: number } = {},
  ): Promise<OperatorOrderList> {
    const search = new URLSearchParams();
    if (params.status) search.set("status", params.status);
    if (params.limit) search.set("limit", String(params.limit));
    if (params.offset) search.set("offset", String(params.offset));
    return apiRequest<OperatorOrderList>(`/v1/backoffice/orders?${search}`, {
      auth: "operator",
      noStore: true,
    });
  },
  operatorOrder(orderId: string): Promise<OperatorOrderDetail> {
    return apiRequest<OperatorOrderDetail>(`/v1/backoffice/orders/${orderId}`, {
      auth: "operator",
      noStore: true,
    });
  },
  transitionShipment(
    orderId: string,
    status: "ready" | "in_transit" | "delivered" | "exception",
  ): Promise<Shipment> {
    return apiRequest<Shipment>(`/v1/backoffice/orders/${orderId}/shipment`, {
      method: "POST",
      body: { status },
      auth: "operator",
      noStore: true,
    });
  },
  cancelOperatorOrder(orderId: string, reason: string): Promise<OrderAdjustmentResult> {
    return apiRequest<OrderAdjustmentResult>(
      `/v1/backoffice/orders/${orderId}/cancel`,
      {
        method: "POST",
        body: { reason },
        auth: "operator",
        noStore: true,
      },
    );
  },
  refundOperatorOrder(
    orderId: string,
    amount: string,
    reason: string,
  ): Promise<OrderAdjustmentResult> {
    return apiRequest<OrderAdjustmentResult>(
      `/v1/backoffice/orders/${orderId}/refund`,
      {
        method: "POST",
        body: { amount, reason },
        auth: "operator",
        noStore: true,
      },
    );
  },
  adjustInventory(
    productId: string,
    quantityDelta: number,
    reason: string,
  ): Promise<InventoryAdjustmentResult> {
    return apiRequest<InventoryAdjustmentResult>(
      `/v1/backoffice/inventory/${productId}/adjustments`,
      {
        method: "POST",
        body: { quantity_delta: quantityDelta, reason },
        auth: "operator",
        noStore: true,
      },
    );
  },
  riskModel(): Promise<FraudModelSummary> {
    return apiRequest<FraudModelSummary>("/v1/backoffice/risk/model", {
      auth: "operator",
      noStore: true,
    });
  },
  decideReview(assessmentId: string, decision: "allow" | "decline"): Promise<ReviewDecisionResult> {
    return apiRequest<ReviewDecisionResult>(
      `/v1/backoffice/risk/${assessmentId}/decision`,
      {
        method: "POST",
        body: { decision },
        auth: "operator",
        noStore: true,
      },
    );
  },
  runSegmentation(): Promise<SegmentationRunResult> {
    return apiRequest<SegmentationRunResult>("/v1/backoffice/segments/run", {
      method: "POST",
      auth: "operator",
      noStore: true,
    });
  },
  async segmentsExport(
    params: { segment?: string; referenceDate?: string } = {},
  ): Promise<{ csv: string; filename: string }> {
    const search = new URLSearchParams();
    if (params.segment) search.set("segment", params.segment);
    if (params.referenceDate) search.set("reference_date", params.referenceDate);
    const token = await readSessionToken("operator");
    if (!token) {
      throw new ApiError("unauthorized", 401, "Sign in to continue.");
    }
    let response: Response;
    try {
      response = await fetch(
        `${API_BASE_URL}/v1/backoffice/segments/export?${search}`,
        {
          headers: {
            authorization: `Bearer ${token}`,
            accept: "text/csv",
          },
          cache: "no-store",
        },
      );
    } catch (error) {
      throw new ApiError(
        "network_error",
        0,
        error instanceof Error ? error.message : "The API service is unreachable.",
      );
    }
    if (!response.ok) {
      let payload: ApiErrorBody = {};
      try {
        payload = (await response.json()) as ApiErrorBody;
      } catch {
        /* CSV failures may not include a JSON envelope. */
      }
      throw new ApiError(
        errorCode(payload.error?.code, response.status),
        response.status,
        payload.error?.message ?? `The API answered ${response.status}.`,
        payload.error?.request_id,
      );
    }
    const disposition = response.headers.get("content-disposition") ?? "";
    const match = /filename="([^"]+)"/.exec(disposition);
    return {
      csv: await response.text(),
      filename: match?.[1] ?? "rfm-segments.csv",
    };
  },
  async login(input: {
    email: string;
    password: string;
    surface: "customer" | "operator";
  }): Promise<AuthSession> {
    return apiRequest<AuthSession>("/v1/auth/login", {
      method: "POST",
      body: input,
      noStore: true,
    });
  },
  async register(input: {
    email: string;
    display_name: string;
    password: string;
    preferred_locale: "ar" | "en";
  }): Promise<AuthSession> {
    return apiRequest<AuthSession>("/v1/auth/register", {
      method: "POST",
      body: input,
      noStore: true,
    });
  },
  me(surface: "customer" | "operator"): Promise<AccountView> {
    return apiRequest<AccountView>("/v1/auth/me", { auth: surface, noStore: true });
  },
  logout(surface: "customer" | "operator"): Promise<void> {
    return apiRequest<void>("/v1/auth/logout", {
      method: "POST",
      auth: surface,
      noStore: true,
    });
  },
  addresses(): Promise<AddressList> {
    return apiRequest<AddressList>("/v1/addresses", {
      auth: "customer",
      noStore: true,
    });
  },
  createAddress(input: {
    label: string;
    recipient_name: string;
    phone: string;
    city: string;
    address_line: string;
    is_default?: boolean;
  }): Promise<Address> {
    return apiRequest<Address>("/v1/addresses", {
      method: "POST",
      body: input,
      auth: "customer",
      noStore: true,
    });
  },
  updateAddress(
    addressId: string,
    input: {
      label: string;
      recipient_name: string;
      phone: string;
      city: string;
      address_line: string;
      is_default: boolean;
    },
  ): Promise<Address> {
    return apiRequest<Address>(`/v1/addresses/${addressId}`, {
      method: "PUT",
      body: input,
      auth: "customer",
      noStore: true,
    });
  },
  deleteAddress(addressId: string): Promise<void> {
    return apiRequest<void>(`/v1/addresses/${addressId}`, {
      method: "DELETE",
      auth: "customer",
      noStore: true,
    });
  },
  account(): Promise<AccountProfile> {
    return apiRequest<AccountProfile>("/v1/account", {
      auth: "customer",
      noStore: true,
    });
  },
  updateAccount(input: {
    display_name?: string;
    preferred_locale?: "ar" | "en";
  }): Promise<AccountProfile> {
    return apiRequest<AccountProfile>("/v1/account", {
      method: "PATCH",
      body: input,
      auth: "customer",
      noStore: true,
    });
  },
  reorder(orderId: string): Promise<ReorderResult> {
    return apiRequest<ReorderResult>(`/v1/orders/${orderId}/reorder`, {
      method: "POST",
      auth: "customer",
      noStore: true,
    });
  },
  cancelOwnOrder(
    orderId: string,
    input: { reason_code: string; reason?: string },
  ): Promise<OrderAdjustmentResult> {
    return apiRequest<OrderAdjustmentResult>(`/v1/orders/${orderId}/cancel`, {
      method: "POST",
      body: input,
      auth: "customer",
      noStore: true,
    });
  },
  changePassword(input: {
    current_password: string;
    new_password: string;
  }): Promise<{ revoked_sessions: number }> {
    return apiRequest<{ revoked_sessions: number }>("/v1/account/password", {
      method: "POST",
      body: input,
      auth: "customer",
      noStore: true,
    });
  },
};
