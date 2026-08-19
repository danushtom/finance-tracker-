/**
 * The only place money division happens (section 6, NFR-5). Every other
 * place in the client treats money as an integer number of minor units.
 */
export function formatCurrency(minor: number, currencyCode: string = "INR"): string {
  const locale = currencyCode === "INR" ? "en-IN" : "en-US";
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency: currencyCode,
    maximumFractionDigits: 0,
  }).format(minor / 100);
}

export function formatDate(iso: string): string {
  const d = new Date(iso);
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "Asia/Kolkata",
  }).format(d);
}

export function currentMonthKey(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

export type ConfidenceBand = "high" | "medium" | "low";

/**
 * Maps the API's numeric 0-100 categorisation confidence (FR-4.3) to a
 * display band.
 *
 * Thresholds mirror the backend pipeline in `app/categorise/engine.py`:
 * exact/user rules score 95-100 and seed rules 90, fuzzy and LLM results
 * land in the 70-88 range, and anything under the default
 * `low_confidence_threshold` of 70 is what lands in the review queue.
 */
export function confidenceBand(confidence: number): ConfidenceBand {
  if (confidence >= 90) return "high";
  if (confidence >= 70) return "medium";
  return "low";
}
