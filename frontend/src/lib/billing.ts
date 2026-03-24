export type InvoiceStatus = "open" | "paid" | "past_due" | "void";
export type PaymentStatus = "pending" | "succeeded" | "failed";

export function isInvoiceOverdue(dueDate: string): boolean {
  const now = new Date();
  const due = new Date(dueDate);

  if (Number.isNaN(due.getTime())) {
    return false;
  }

  return due.getTime() < now.getTime();
}

export function calculateOutstandingAmount(
  totalAmount: number,
  paidAmount: number
): number {
  const remaining = totalAmount - paidAmount;
  return remaining > 0 ? remaining : 0;
}

export function getInvoiceStatusLabel(status: InvoiceStatus): string {
  switch (status) {
    case "open":
      return "Open";
    case "paid":
      return "Paid";
    case "past_due":
      return "Past Due";
    case "void":
      return "Voided";
    default:
      return status;
  }
}

export function getPaymentStatusLabel(status: PaymentStatus): string {
  switch (status) {
    case "pending":
      return "Pending";
    case "succeeded":
      return "Succeeded";
    case "failed":
      return "Failed";
    default:
      return status;
  }
}