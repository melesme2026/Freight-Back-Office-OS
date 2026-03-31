export type InvoiceStatus = "open" | "paid" | "past_due" | "void";
export type PaymentStatus = "pending" | "succeeded" | "failed";

function toFiniteNumber(value: number): number {
  return Number.isFinite(value) ? value : 0;
}

function parseDueDate(value: string): Date | null {
  const trimmed = value.trim();

  if (trimmed.length === 0) {
    return null;
  }

  const dateOnlyMatch = /^(\d{4})-(\d{2})-(\d{2})$/.exec(trimmed);
  if (dateOnlyMatch) {
    const [, yearText, monthText, dayText] = dateOnlyMatch;
    const year = Number(yearText);
    const monthIndex = Number(monthText) - 1;
    const day = Number(dayText);

    const localEndOfDay = new Date(year, monthIndex, day, 23, 59, 59, 999);
    return Number.isNaN(localEndOfDay.getTime()) ? null : localEndOfDay;
  }

  const parsed = new Date(trimmed);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

export function isInvoiceOverdue(dueDate: string): boolean {
  const due = parseDueDate(dueDate);

  if (!due) {
    return false;
  }

  return due.getTime() < Date.now();
}

export function calculateOutstandingAmount(
  totalAmount: number,
  paidAmount: number
): number {
  const normalizedTotal = toFiniteNumber(totalAmount);
  const normalizedPaid = toFiniteNumber(paidAmount);
  const remaining = normalizedTotal - normalizedPaid;

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
  }
}