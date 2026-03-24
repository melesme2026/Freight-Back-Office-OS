export function isValidEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
}

export function isValidPhone(value: string): boolean {
  const digits = value.replace(/\D+/g, "");
  return digits.length >= 10 && digits.length <= 15;
}

export function isRequired(value: string | null | undefined): boolean {
  return Boolean(value && value.trim().length > 0);
}

export function minLength(value: string, min: number): boolean {
  return value.trim().length >= min;
}