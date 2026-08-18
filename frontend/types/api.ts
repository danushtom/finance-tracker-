/**
 * Hand-authored API types mirroring the backend's Pydantic schemas.
 *
 * TODO: once the API is running, replace this file by running
 * `npm run generate-types` (openapi-typescript against the live
 * `/openapi.json`) — per NFR-18, hand-written duplicate types are meant to
 * be a bootstrapping step only, not the long-term source of truth.
 */

export type ObjectIdStr = string;
export type Minor = number; // integer paise (NFR-5) — never divide outside lib/format.ts

// ---- Auth -------------------------------------------------------------

export interface LLMSettingsOut {
  provider: "gemini" | "claude" | "none";
  monthly_call_cap: number;
  gemini_api_key_set: boolean;
  gemini_api_key_masked: string | null;
  claude_api_key_set: boolean;
  claude_api_key_masked: string | null;
}

export interface VariableSplit {
  invest_pct: number;
  goals_pct: number;
  discretionary_pct: number;
}

export interface UserSettingsOut {
  currency: string;
  timezone: string;
  month_start_day: number;
  buffer_minor: Minor;
  low_confidence_threshold: number;
  monthly_savings_target_minor: Minor;
  monthly_investment_target_minor: Minor;
  variable_split: VariableSplit;
  count_expected_salary: boolean;
  llm: LLMSettingsOut;
}

export interface User {
  id: ObjectIdStr;
  email: string;
  display_name: string;
  settings: UserSettingsOut;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// ---- Accounts -----------------------------------------------------------

export type AccountType =
  | "bank"
  | "cash"
  | "credit_card"
  | "brokerage"
  | "mf_folio"
  | "ppf_epf"
  | "asset"
  | "liability";

export interface Account {
  _id: ObjectIdStr;
  user_id: ObjectIdStr;
  name: string;
  type: AccountType;
  institution: string | null;
  last4: string | null;
  current_balance_minor: Minor;
  balance_as_of: string | null;
  is_asset: boolean;
  archived: boolean;
  created_at: string;
  updated_at: string;
}

// ---- Categories & rules ---------------------------------------------------

export type CategoryClass = "fixed" | "variable" | "isolated" | "income" | "transfer" | "investment";

export interface Category {
  _id: ObjectIdStr;
  user_id: ObjectIdStr;
  name: string;
  parent_id: ObjectIdStr | null;
  class: CategoryClass;
  colour: string | null;
  icon: string | null;
  is_system: boolean;
  archived: boolean;
  sort_order: number;
}

export type MatchType = "exact" | "contains" | "starts_with" | "regex";

export interface Rule {
  _id: ObjectIdStr;
  user_id: ObjectIdStr;
  match_type: MatchType;
  pattern: string;
  direction: string | null;
  amount_min_minor: Minor | null;
  amount_max_minor: Minor | null;
  category_id: ObjectIdStr;
  subcategory_id: ObjectIdStr | null;
  priority: number;
  source: "user" | "seed" | "llm_confirmed";
  enabled: boolean;
  hit_count: number;
}

export interface Merchant {
  _id: ObjectIdStr;
  merchant_norm: string;
  display_name: string;
  category_id: ObjectIdStr | null;
  confidence: number;
  source: "user" | "llm" | "seed";
  txn_count: number;
  last_seen: string | null;
}

// ---- Transactions & imports -----------------------------------------------

export interface Transaction {
  _id: ObjectIdStr;
  account_id: ObjectIdStr;
  import_id: ObjectIdStr | null;
  date: string;
  description_raw: string;
  merchant_norm: string;
  amount_minor: Minor;
  direction: "debit" | "credit";
  kind: "expense" | "income" | "transfer" | "investment" | "refund";
  category_id: ObjectIdStr | null;
  category_class: CategoryClass | null;
  confidence: number;
  categorised_by: "rule" | "fuzzy" | "llm" | "user" | "none";
  needs_review: boolean;
  note: string | null;
  is_manual: boolean;
}

export type ImportStatus =
  | "queued"
  | "parsing"
  | "needs_mapping"
  | "categorising"
  | "needs_review"
  | "completed"
  | "failed";

export interface ImportSummary {
  rows_found: number;
  imported: number;
  duplicates_skipped: number;
  failed: number;
  date_from: string | null;
  date_to: string | null;
  llm_calls: number;
  needs_review_count: number;
}

export interface ImportRecord {
  _id: ObjectIdStr;
  account_id: ObjectIdStr;
  filename: string;
  status: ImportStatus;
  parser: string | null;
  summary: ImportSummary;
  preview: Record<string, string>[];
  created_at: string;
}

// ---- Dashboard / Safe-to-Spend --------------------------------------------

export interface WaterfallLine {
  label: string;
  amount_minor: Minor;
  sign: "+" | "-";
  drilldown: Record<string, unknown> | null;
}

export interface SafeToSpend {
  month: string;
  amount_minor: Minor;
  is_over: boolean;
  over_by_minor: Minor;
  per_day_minor: Minor | null;
  days_left: number;
  lines: WaterfallLine[];
}

export interface CategoryBreakdownRow {
  category_id: ObjectIdStr | null;
  category_name: string;
  class: CategoryClass;
  total_minor: Minor;
  count: number;
}

export interface DashboardPayload {
  month: string;
  baseline_income_minor: Minor;
  variable_income_minor: Minor;
  spent_minor: Minor;
  saved_minor: Minor;
  invested_minor: Minor;
  available_minor: Minor;
  safe_to_spend: SafeToSpend;
  isolated: CategoryBreakdownRow[];
  fixed_due_minor: Minor;
  fixed_paid_minor: Minor;
  fixed_commitments: {
    id: string;
    display_name: string;
    expected_amount_minor: Minor;
    next_expected_date: string | null;
  }[];
  category_breakdown: CategoryBreakdownRow[];
  review_queue_count: number;
  top_goals: { id: string; name: string; target_amount_minor: Minor; current_amount_minor: Minor; priority: string }[];
  top_wishlist: { id: string; name: string; price_minor: Minor; priority: string }[];
}

// ---- Wishlist / goals / investments ----------------------------------------

export interface WishlistVerdict {
  item_id: ObjectIdStr;
  name: string;
  price_minor: Minor;
  priority: "high" | "medium" | "low";
  affordable: boolean;
  remaining_after_purchase_minor: Minor | null;
  shortfall_minor: Minor;
  months_to_afford: number | null;
  on_current_cash_flow: boolean;
}

export interface Goal {
  _id: ObjectIdStr;
  name: string;
  target_amount_minor: Minor;
  current_amount_minor: Minor;
  target_date: string | null;
  priority: "high" | "medium" | "low";
  monthly_reservation_minor: Minor;
  is_emergency_fund: boolean;
  status: string;
}

export interface GoalWithProgress {
  goal: Goal;
  progress: {
    percentage: number;
    on_track: "ahead" | "on_track" | "behind" | null;
    required_monthly_minor: Minor | null;
  };
}

export interface Investment {
  _id: ObjectIdStr;
  name: string;
  type: string;
  invested_minor: Minor;
  current_value_minor: Minor;
  identifier: string | null;
  value_as_of: string | null;
  archived: boolean;
}

export interface Commitment {
  _id: ObjectIdStr;
  merchant_norm: string;
  display_name: string;
  expected_amount_minor: Minor;
  cadence: string;
  next_expected_date: string | null;
  status: "detected" | "confirmed" | "cancelled";
}

export interface IncomeSource {
  _id: ObjectIdStr;
  name: string;
  type: "baseline" | "variable";
  expected_amount_minor: Minor | null;
  cadence: string;
  match_patterns: string[];
  active: boolean;
}

export interface AdvisorSummary {
  has_enough_data: boolean;
  months_of_data: number;
  baseline_income_minor: Minor;
  median_fixed_minor: Minor;
  median_variable_minor: Minor;
  recommended_allocation_minor: Minor;
  sentence: string;
}
