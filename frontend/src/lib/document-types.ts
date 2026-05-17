export type CanonicalDocumentType =
  | "rate_confirmation"
  | "bill_of_lading"
  | "proof_of_delivery"
  | "invoice"
  | "lumper_receipt"
  | "fuel_receipt"
  | "detention_support"
  | "scale_ticket"
  | "accessorial_support"
  | "payment_remittance"
  | "notice_of_assignment"
  | "w9"
  | "certificate_of_insurance"
  | "damage_claim_photo"
  | "other"
  | "unknown";

const DOCUMENT_TYPE_ALIASES: Record<string, CanonicalDocumentType> = {
  unknown: "unknown",
  ratecon: "rate_confirmation",
  "rate con": "rate_confirmation",
  rate_confirmation: "rate_confirmation",
  "rate-confirmation": "rate_confirmation",
  "rate confirmation": "rate_confirmation",
  rate_confirmation_pdf: "rate_confirmation",
  "rate confirmation pdf": "rate_confirmation",
  rc: "rate_confirmation",
  bol: "bill_of_lading",
  bill_of_lading: "bill_of_lading",
  "bill-of-lading": "bill_of_lading",
  "bill of lading": "bill_of_lading",
  pod: "proof_of_delivery",
  proof_of_delivery: "proof_of_delivery",
  "proof-of-delivery": "proof_of_delivery",
  "proof of delivery": "proof_of_delivery",
  delivery_receipt: "proof_of_delivery",
  "delivery receipt": "proof_of_delivery",
  signed_pod: "proof_of_delivery",
  "signed pod": "proof_of_delivery",
  invoice: "invoice",
  freight_invoice: "invoice",
  "freight invoice": "invoice",
  generated_invoice: "invoice",
  "generated invoice": "invoice",
  lumper_receipt: "lumper_receipt",
  "lumper receipt": "lumper_receipt",
  fuel_receipt: "fuel_receipt",
  "fuel receipt": "fuel_receipt",
  fuel: "fuel_receipt",
  detention_support: "detention_support",
  "detention support": "detention_support",
  scale_ticket: "scale_ticket",
  "scale ticket": "scale_ticket",
  accessorial_support: "accessorial_support",
  "accessorial support": "accessorial_support",
  payment_remittance: "payment_remittance",
  "payment remittance": "payment_remittance",
  notice_of_assignment: "notice_of_assignment",
  "notice of assignment": "notice_of_assignment",
  w9: "w9",
  "w-9": "w9",
  certificate_of_insurance: "certificate_of_insurance",
  "certificate of insurance": "certificate_of_insurance",
  damage_claim_photo: "damage_claim_photo",
  "damage claim photo": "damage_claim_photo",
  other: "other",
};

const DOCUMENT_TYPE_LABELS: Record<CanonicalDocumentType, string> = {
  rate_confirmation: "Rate Confirmation",
  bill_of_lading: "Bill of Lading",
  proof_of_delivery: "Proof of Delivery",
  invoice: "Invoice",
  lumper_receipt: "Lumper Receipt",
  fuel_receipt: "Fuel Receipt",
  detention_support: "Detention Support",
  scale_ticket: "Scale Ticket",
  accessorial_support: "Accessorial Support",
  payment_remittance: "Payment Remittance",
  notice_of_assignment: "Notice of Assignment",
  w9: "W-9",
  certificate_of_insurance: "Certificate of Insurance",
  damage_claim_photo: "Damage Claim Photo",
  other: "Other",
  unknown: "Unknown",
};

function normalizeKey(value?: string | null): string {
  return (value ?? "")
    .trim()
    .toLowerCase()
    .replace(/[./]+/g, " ")
    .replace(/\s+/g, " ");
}

export function canonicalDocumentType(value?: string | null): CanonicalDocumentType {
  const normalized = normalizeKey(value);
  if (!normalized) return "unknown";
  const candidates = [
    normalized,
    normalized.replaceAll(" ", "_"),
    normalized.replaceAll(" ", "-"),
    normalized.replaceAll("-", "_"),
    normalized.replaceAll("_", " "),
  ];
  for (const candidate of candidates) {
    const matched = DOCUMENT_TYPE_ALIASES[candidate];
    if (matched) return matched;
  }
  return "unknown";
}

export function documentTypeLabel(value?: string | null): string {
  const canonical = canonicalDocumentType(value);
  if (canonical !== "unknown") return DOCUMENT_TYPE_LABELS[canonical];
  return value && value.trim().length > 0 ? value : DOCUMENT_TYPE_LABELS.unknown;
}

export function isDocumentType(value: string | null | undefined, aliases: string[]): boolean {
  const canonical = canonicalDocumentType(value);
  return aliases.some((alias) => canonicalDocumentType(alias) === canonical);
}
