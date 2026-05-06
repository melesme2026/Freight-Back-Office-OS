export type ParsedUploadError = {
  duplicate: boolean;
  message: string;
  code?: string;
};

type UploadErrorDetail = {
  code?: string;
  message?: string;
  existing_document_id?: string;
  document_type?: string;
  can_replace?: boolean;
};

type UploadErrorPayload = {
  detail?: string | UploadErrorDetail;
  error?: {
    code?: string;
    message?: string;
    details?: { detail?: UploadErrorDetail } & Record<string, unknown>;
  };
  message?: string;
};

export function isHtmlErrorText(value: string) {
  return /<!doctype html|<html[\s>]|<body[\s>]|nginx|render gateway/i.test(value.trim());
}

function cleanMessage(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  if (!trimmed || isHtmlErrorText(trimmed)) return null;
  return trimmed;
}

export function parseUploadErrorText(
  responseText: string,
  fallback: string,
  status?: number,
): ParsedUploadError {
  let parsed: UploadErrorPayload | null = null;

  try {
    parsed = responseText.trim().length > 0 ? (JSON.parse(responseText) as UploadErrorPayload) : null;
  } catch {
    parsed = null;
  }

  const directDetail = typeof parsed?.detail === "object" ? parsed.detail : undefined;
  const duplicateDetail = directDetail ?? parsed?.error?.details?.detail;
  if (status === 409 && duplicateDetail?.code === "duplicate_required_document") {
    return {
      duplicate: true,
      code: duplicateDetail.code,
      message: cleanMessage(duplicateDetail.message) ?? "A required document already exists for this load.",
    };
  }

  const detailMessage = typeof parsed?.detail === "string" ? parsed.detail : directDetail?.message;
  const message =
    cleanMessage(parsed?.error?.message) ??
    cleanMessage(parsed?.message) ??
    cleanMessage(detailMessage) ??
    cleanMessage(responseText) ??
    fallback;

  return { duplicate: false, message, code: parsed?.error?.code ?? directDetail?.code };
}

export async function parseUploadErrorResponse(
  response: Response,
  fallback: string,
): Promise<ParsedUploadError> {
  const responseText = await response.text();
  return parseUploadErrorText(responseText, fallback, response.status);
}
