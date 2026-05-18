export const brand = {
  names: {
    platform: "Freight Back Office OS",
    company: "Adwa Freight",
    operatingSystem: "Adwa Freight OS",
  },
  colors: {
    operationalPrimary: "#10233f",
    operationalPrimaryLight: "#183a66",
    operationalAccent: "#2f80ed",
    routeCyan: "#31c4b3",
    success: "#147d64",
    warning: "#b7791f",
    danger: "#c2413d",
    neutral900: "#111827",
    neutral700: "#334155",
    neutral500: "#64748b",
    neutral100: "#e5edf5",
    neutral50: "#f6f8fb",
  },
  typography: {
    sans: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    mono: "'SFMono-Regular', 'Roboto Mono', Consolas, 'Liberation Mono', monospace",
  },
  radii: {
    card: "24px",
    control: "14px",
    chip: "999px",
  },
  pdf: {
    logo: "/brand/adwa-freight-os-horizontal-light.svg",
    monochromeLogo: "/brand/adwa-freight-os-horizontal-ink.svg",
    headerHeight: 72,
    footerHeight: 48,
    margin: 40,
    fontFamily: "Inter, Arial, sans-serif",
  },
} as const;

export type BrandNameVariant = "platform" | "company" | "operatingSystem";
