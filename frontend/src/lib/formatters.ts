export function formatCurrency(
  value: number | string,
  currency: string = "USD",
  locale: string = "en-US"
): string {
  const numericValue =
    typeof value === "number" ? value : Number.parseFloat(String(value));

  if (Number.isNaN(numericValue)) {
    return `${currency} 0.00`;
  }

  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
  }).format(numericValue);
}

export function formatDate(
  value: string | Date,
  locale: string = "en-US"
): string {
  const date = value instanceof Date ? value : new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return new Intl.DateTimeFormat(locale, {
    year: "numeric",
    month: "short",
    day: "2-digit",
  }).format(date);
}

export function formatDateTime(
  value: string | Date,
  locale: string = "en-US"
): string {
  const date = value instanceof Date ? value : new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return new Intl.DateTimeFormat(locale, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

export function toTitleCase(value: string): string {
  return value
    .replace(/[_-]+/g, " ")
    .split(" ")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}