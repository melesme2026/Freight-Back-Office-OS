export const LOAD_STATUSES = [
  "booked",
  "in_transit",
  "delivered",
  "docs_received",
  "docs_needs_attention",
  "invoice_ready",
  "submitted_to_broker",
  "submitted_to_factoring",
  "packet_rejected",
  "resubmission_needed",
  "advance_paid",
  "reserve_pending",
  "fully_paid",
  "short_paid",
  "disputed",
  "archived",
] as const;

export type LoadStatus = (typeof LOAD_STATUSES)[number];
