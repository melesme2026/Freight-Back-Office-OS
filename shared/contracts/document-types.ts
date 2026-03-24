export const DOCUMENT_TYPES = [
  "unknown",
  "rate_confirmation",
  "bill_of_lading",
  "proof_of_delivery",
  "invoice",
  "other",
] as const;

export type DocumentType = (typeof DOCUMENT_TYPES)[number];