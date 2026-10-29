/** Response types mirroring the published FastAPI contracts. */

export type Locale = "ar" | "en";

export type AvailabilityStatus = "in_stock" | "out_of_stock";

export interface Price {
  amount: string;
  currency: string;
  updated_at: string;
}

export interface Availability {
  status: AvailabilityStatus;
  updated_at: string;
}

export interface ProductImage {
  uri: string;
  alt: string;
}

export interface Product {
  product_id: string;
  name: string;
  description: string;
  categories: string[];
  attributes: Record<string, string>;
  images: ProductImage[];
  price: Price;
  availability: Availability;
}

export interface ProductPage {
  items: Product[];
  total: number;
  limit: number;
  offset: number;
}

export interface FacetOption {
  value: string;
  count: number;
}

export interface Facet {
  key: string;
  options: FacetOption[];
}

export interface CatalogFacets {
  total: number;
  facets: Facet[];
}

export interface RecommendationBasis {
  browsing_events: number;
  purchased_items: number;
}

export interface RecommendationResult {
  items: string[];
  strategy: string;
  model_version: string;
  basis: RecommendationBasis;
}

export interface CartItem {
  product_id: string;
  quantity: number;
  unit_price: string;
  available: number;
}

export interface Cart {
  cart_id: string;
  items: CartItem[];
  currency: "EGP";
  subtotal: string;
}

export type OrderState =
  | "pending_payment"
  | "pending_risk"
  | "review"
  | "confirmed"
  | "payment_failed"
  | "cancelled"
  | "shipped"
  | "delivered"
  | "refunded";

export interface OrderStatus {
  order_id: string;
  status: OrderState;
}

export interface OrderItem {
  product_id: string;
  product_name: string;
  quantity: number;
  unit_price: string;
  line_total: string;
}

export interface Order {
  order_id: string;
  status: OrderState;
  currency: "EGP";
  subtotal: string;
  created_at: string;
  items: OrderItem[];
}

export interface OrderSummary {
  order_id: string;
  status: OrderState;
  currency: "EGP";
  subtotal: string;
  item_count: number;
  created_at: string;
}

export interface OrderList {
  items: OrderSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface OperatorCustomer {
  customer_id: string;
  email: string;
  display_name: string;
}

export interface OperatorShipping {
  recipient_name: string | null;
  phone: string | null;
  city: string | null;
  address_line: string | null;
}

export interface OperatorOrderSummary {
  order_id: string;
  status: OrderState;
  currency: "EGP";
  subtotal: string;
  refund_total: string;
  item_count: number;
  created_at: string;
  customer: OperatorCustomer;
}

export interface OperatorOrderList {
  items: OperatorOrderSummary[];
  total: number;
  limit: number;
  offset: number;
  status: OrderState | null;
}

export interface OrderAdjustment {
  adjustment_id: string;
  kind: "cancellation" | "refund";
  amount: string;
  reason: string;
  reason_code: string | null;
  actor_kind: "customer" | "operator";
  actor_name: string;
  created_at: string;
}

export interface OperatorOrderDetail {
  order_id: string;
  status: OrderState;
  currency: "EGP";
  subtotal: string;
  refund_total: string;
  created_at: string;
  completed_at: string | null;
  customer: OperatorCustomer;
  shipping: OperatorShipping | null;
  items: OrderItem[];
  shipment: Shipment | null;
  adjustments: OrderAdjustment[];
}

export interface AccountProfile {
  customer_id: string;
  email: string;
  display_name: string;
  preferred_locale: "ar" | "en";
  member_since: string;
  order_count: number;
}

export interface AccountView {
  principal_id: string;
  account_type: "customer" | "backoffice";
  customer_id: string | null;
  scopes: string[];
  profile: AccountProfile | null;
}

export interface AuthSession {
  token: string;
  surface: "customer" | "operator";
  expires_at: string;
  account: AccountView;
}

export type ShipmentStatus =
  | "pending"
  | "ready"
  | "in_transit"
  | "delivered"
  | "exception";

export interface ShipmentEvent {
  status: ShipmentStatus;
  description_ar: string;
  description_en: string;
  occurred_at: string;
}

export interface Shipment {
  shipment_id: string;
  status: ShipmentStatus;
  updated_at: string;
  events: ShipmentEvent[];
}

export interface OrderAdjustmentResult {
  order_id: string;
  status: OrderState;
  refund_total: string;
  adjustment_id: string;
  kind: "cancellation" | "refund";
  amount: string;
  created_at: string;
}

export interface InventoryAdjustmentResult {
  product_id: string;
  on_hand: number;
  reserved: number;
  available: number;
  movement_id: string;
  occurred_at: string;
}

export interface AssistantSource {
  kind: "faq" | "product" | "shipment";
  reference: string;
  label: string;
}

export interface AssistantResponse {
  answer: string;
  model: string;
  sources: AssistantSource[];
}

export interface ImageSearchItem {
  product: Product;
  score: number;
}

export interface ImageSearchResponse {
  items: ImageSearchItem[];
  model_version: string;
}

export interface VoiceSearchResponse {
  transcript: string;
  items: Product[];
  total: number;
  model: string;
}

export interface InventoryPolicy {
  version: string;
  forecast_days: number;
  lead_time_days: number;
  safety_stock_days: number;
  target_cover_days: number;
}

export interface DemandForecast {
  forecast_id: string;
  horizon_start: string;
  horizon_end: string;
  predicted_quantity: string;
  model_version: string;
  generated_at: string;
}

export interface ReorderRecord {
  reorder_id: string;
  quantity: number;
  status: "created" | "dispatched" | "acknowledged" | "failed" | "received";
  supplier_reference: string | null;
  simulator: boolean;
  status_detail: string | null;
  last_attempted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface InventoryPlanningItem {
  product_id: string;
  on_hand: number;
  reserved: number;
  available: number;
  pending_replenishment: number;
  inventory_position: number;
  forecast: DemandForecast | null;
  reorder_point: number | null;
  target_stock: number | null;
  latest_reorder: ReorderRecord | null;
  planning_status: "forecast_missing" | "planned" | "reorder_pending" | "supplier_failed";
}

export interface InventoryPlanningResponse {
  generated_at: string;
  policy: InventoryPolicy;
  items: InventoryPlanningItem[];
}

export interface ReorderRunItem {
  product_id: string;
  forecast_id: string | null;
  predicted_quantity: string | null;
  reorder_id: string | null;
  reorder_quantity: number;
  outcome: string;
}

export interface ReorderRunResult {
  run_date: string;
  model_version: string;
  forecasts_generated: number;
  reorders_created: number;
  reorders_reused: number;
  adequate_stock: number;
  insufficient_history: number;
  items: ReorderRunItem[];
}

export type PricingInputStatus = "fresh" | "stale" | "missing";

export interface PricingPolicy {
  version: string;
  max_change_ratio: string;
  minimum_margin_ratio: string;
  demand_weight: string;
  competitor_weight: string;
  freshness_hours: number;
  rounding: string;
  rules: string[];
}

export interface PricingSeason {
  season_id: string;
  label_en: string;
  label_ar: string;
  price_multiplier: string;
  starts_on: string | null;
  ends_on: string | null;
}

export interface PricingObservation {
  observation_id: string;
  recorded_cost: string;
  supply: string;
  demand: string;
  competitor_cost: string;
  observed_season_id: string;
  provenance: string;
  observed_at: string;
  fresh: boolean;
}

export interface PriceChange {
  price_change_id: string;
  product_id: string;
  old_amount: string;
  new_amount: string;
  currency: string;
  calculation_version: string;
  applied_at: string;
  contributing_inputs: Record<string, unknown>;
}

export interface PricingOverviewItem {
  product_id: string;
  currency: string;
  current_amount: string;
  price_updated_at: string;
  input_status: PricingInputStatus;
  observation: PricingObservation | null;
  outcome: string;
  detail: string | null;
  proposed_amount: string | null;
  latest_change: PriceChange | null;
}

export interface PricingOverviewResponse {
  generated_at: string;
  as_of: string;
  season: PricingSeason;
  policy: PricingPolicy;
  items: PricingOverviewItem[];
  recent_changes: PriceChange[];
}

export interface PricingRunItem {
  product_id: string;
  outcome: string;
  detail: string | null;
  old_amount: string | null;
  new_amount: string | null;
}

export interface PricingRunResult {
  run_date: string;
  policy_version: string;
  season_id: string;
  evaluated: number;
  updated: number;
  unchanged: number;
  missing_input: number;
  stale_input: number;
  constraint_blocked: number;
  already_applied: number;
  conflict: number;
  items: PricingRunItem[];
}

export interface PricingObservationResult {
  observation_id: string;
  product_id: string;
  observed_at: string;
  season_id: string;
  provenance: string;
}

export type SegmentName =
  | "champions"
  | "loyal"
  | "potential"
  | "new"
  | "at_risk"
  | "hibernating";

export interface SegmentRule {
  segment: SegmentName;
  rule: string;
}

export interface RfmPolicy {
  version: string;
  window_days: number;
  eligible_statuses: string[];
  excluded_statuses: string[];
  minimum_cohort_size: number;
  scoring: string;
  rules: SegmentRule[];
}

export interface SegmentCount {
  segment: SegmentName;
  customers: number;
}

export interface CustomerSegment {
  customer_id: string;
  email: string;
  display_name: string;
  reference_date: string;
  recency_days: number;
  frequency: number;
  monetary: string;
  recency_score: number;
  frequency_score: number;
  monetary_score: number;
  segment: SegmentName;
}

export interface SegmentationResponse {
  snapshot_available: boolean;
  reference_date: string | null;
  observation_start: string | null;
  generated_at: string | null;
  stale: boolean;
  policy: RfmPolicy;
  cohort_size: number;
  insufficient_history: number;
  counts: SegmentCount[];
  members: CustomerSegment[];
  total_members: number;
  limit: number;
  offset: number;
}

export interface SegmentationRunResult {
  reference_date: string;
  observation_start: string;
  policy_version: string;
  classified: number;
  insufficient_history: number;
  eligible_orders: number;
  excluded_orders: number;
  cohort_size: number;
  counts: SegmentCount[];
}

export interface ReviewQueueItem {
  assessment_id: string;
  order_id: string;
  customer_id: string;
  score: string | null;
  outcome: "review" | "assessment_failed";
  subtotal: string;
  assessed_at: string;
  model_version: string | null;
  reasons: string[];
}

export interface FraudModelSummary {
  model_version_id: string;
  version_label: string;
  dataset_snapshot_id: string;
  threshold: string;
  feature_names: string[];
  metrics: Record<string, number>;
  limitations: string;
  trained_at: string | null;
}

export interface ReviewDecisionResult {
  assessment_id: string;
  order_id: string;
  status: OrderState;
}

export interface AnalyticsScope {
  date_from: string;
  date_to: string;
  category: string | null;
  category_product_count: number;
}

export interface BehaviourMetrics {
  product_views: number;
  sessions: number;
  add_to_carts: number;
  created_orders: number;
  orders_per_session: string;
  unfulfilled_orders: number;
}

export interface FinancialMetrics {
  order_count: number;
  gross_sales: string;
  refunds: string;
  net_sales: string;
  average_order_value: string;
  currency: string;
}

export interface ProductPerformance {
  product_id: string;
  views: number;
  add_to_carts: number;
  units: number;
  revenue: string;
}

export interface DailyPoint {
  day: string;
  views: number;
  sessions: number;
  orders: number;
  net_sales: string;
}

export interface ReconciliationCheck {
  metric: string;
  reported: string;
  recomputed: string;
  matches: boolean;
  source: string;
}

export interface AnalyticsResponse {
  generated_at: string;
  scope: AnalyticsScope;
  behaviour: BehaviourMetrics;
  financial: FinancialMetrics;
  top_products: ProductPerformance[];
  daily: DailyPoint[];
  reconciliation: ReconciliationCheck[];
  no_events: boolean;
  no_orders: boolean;
  category_without_products: boolean;
  definitions: string[];
}
