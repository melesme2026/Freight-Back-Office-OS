export const CHANNEL_TYPES = [
  "manual",
  "whatsapp",
  "email",
  "api",
  "system",
] as const;

export type ChannelType = (typeof CHANNEL_TYPES)[number];