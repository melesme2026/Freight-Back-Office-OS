export function toDriverStatus(rawStatus: string | null | undefined, hasMissingDocs: boolean): string {
  const normalized = (rawStatus ?? "").trim().toLowerCase();

  if (hasMissingDocs) {
    return "docs needed";
  }

  if (["booked"].includes(normalized)) return "booked";
  if (["in_transit"].includes(normalized)) return "in transit";
  if (["delivered", "docs_received", "invoice_ready"].includes(normalized)) return "delivered";
  if (["submitted_to_broker", "submitted_to_factoring"].includes(normalized)) return "submitted";
  if (["fully_paid"].includes(normalized)) return "paid";
  return "in transit";
}

export function labelForDocumentType(documentType: string): string {
  const map: Record<string, string> = {
    rate_confirmation: "Rate Confirmation",
    bill_of_lading: "Bill of Lading",
    proof_of_delivery: "Proof of Delivery",
    lumper_receipt: "Lumper Receipt",
    scale_ticket: "Scale Ticket",
    other: "Other Supporting Docs",
  };

  return map[documentType] ?? documentType;
}
