export const LOAD_STATUSES = [
  "new",
  "docs_received",
  "extracting",
  "needs_review",
  "validated",
  "ready_to_submit",
  "submitted",
  "funded",
  "paid",
  "exception",
  "archived",
] as const;

export type LoadStatus = (typeof LOAD_STATUSES)[number];