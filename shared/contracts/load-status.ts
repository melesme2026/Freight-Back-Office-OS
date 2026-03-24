export const LOAD_STATUSES = [
  "draft",
  "documents_pending",
  "under_review",
  "validated",
  "submitted",
  "invoiced",
  "paid",
  "closed",
] as const;

export type LoadStatus = (typeof LOAD_STATUSES)[number];