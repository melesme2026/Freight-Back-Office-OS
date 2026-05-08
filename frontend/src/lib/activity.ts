import { apiClient } from "@/lib/api-client";

export type ActivityEvent = {
  id: string;
  actor_type: string;
  actor_id: string | null;
  entity_type: string;
  entity_id: string;
  action: string;
  metadata: Record<string, unknown>;
  created_at: string | null;
};

type ApiEnvelope = {
  data?: unknown;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function normalizeEvent(value: unknown): ActivityEvent | null {
  if (!isRecord(value)) {
    return null;
  }

  return {
    id: String(value.id ?? ""),
    actor_type: String(value.actor_type ?? "system"),
    actor_id: typeof value.actor_id === "string" ? value.actor_id : null,
    entity_type: String(value.entity_type ?? "activity"),
    entity_id: String(value.entity_id ?? ""),
    action: String(value.action ?? "activity.recorded"),
    metadata: isRecord(value.metadata) ? value.metadata : {},
    created_at: typeof value.created_at === "string" ? value.created_at : null,
  };
}

export async function fetchRecentActivity(limit = 20): Promise<ActivityEvent[]> {
  const response = await apiClient.get<ApiEnvelope | ActivityEvent[]>(`/activity?limit=${limit}`);
  const rawItems = Array.isArray(response) ? response : Array.isArray(response?.data) ? response.data : [];
  return rawItems.map(normalizeEvent).filter((item): item is ActivityEvent => item !== null && Boolean(item.id));
}

export function formatActivityAction(action: string): string {
  return action
    .split(".")
    .map((part) => part.replace(/_/g, " "))
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" · ");
}
