import Image from "next/image";

import type { BrandNameVariant } from "@/lib/theme/brand";

type BrandLogoProps = {
  variant?: BrandNameVariant;
  tone?: "light" | "dark" | "ink";
  lockup?: "horizontal" | "mark";
  className?: string;
  priority?: boolean;
};

const logoMap: Record<BrandNameVariant, string> = {
  platform: "freight-back-office-os",
  company: "adwa-freight",
  operatingSystem: "adwa-freight-os",
};

const altMap: Record<BrandNameVariant, string> = {
  platform: "Freight Back Office OS",
  company: "Adwa Freight",
  operatingSystem: "Adwa Freight OS",
};

export function BrandLogo({
  variant = "operatingSystem",
  tone = "light",
  lockup = "horizontal",
  className,
  priority = false,
}: BrandLogoProps) {
  const isMark = lockup === "mark";
  const src = isMark ? `/brand/adwa-mark-${tone}.svg` : `/brand/${logoMap[variant]}-horizontal-${tone}.svg`;
  const width = isMark ? 44 : 224;
  const height = isMark ? 44 : 48;

  return (
    <Image
      src={src}
      width={width}
      height={height}
      alt={isMark ? "Adwa Freight mark" : altMap[variant]}
      className={className ?? (isMark ? "h-11 w-11" : "h-12 w-auto")}
      priority={priority}
    />
  );
}

export function BrandMark({ tone = "light", className }: Pick<BrandLogoProps, "tone" | "className">) {
  return <BrandLogo lockup="mark" tone={tone} className={className} />;
}
