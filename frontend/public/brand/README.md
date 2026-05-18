# Adwa Freight OS Brand Asset System

This directory contains the first production brand system for Freight Back Office OS / Adwa Freight.

## Logo lockups

- `adwa-freight-os-horizontal-light.svg` — primary app, marketing, invoice, and email lockup on light backgrounds.
- `adwa-freight-os-horizontal-dark.svg` — primary lockup for dark marketing headers and high-contrast hero surfaces.
- `adwa-freight-os-horizontal-ink.svg` — monochrome-safe lockup for PDF exports, low-color email clients, and operational documents.
- `freight-back-office-os-horizontal-*` — product-name lockups where the platform name is required.
- `adwa-freight-horizontal-*` — company-name lockups for business documents or partner-facing use.

## Mark and app icon

- `adwa-mark-light.svg`, `adwa-mark-dark.svg`, and `adwa-mark-ink.svg` are compact route-orchestration marks.
- `/brand/adwa-mark-light.svg` and `/icons/driver-icon.svg` are SVG-only app-safe icons for manifest, mobile, and PWA surfaces.
- Existing binary favicon files are intentionally not changed in this PR so the final diff remains SVG-only.

## Usage guidance

Use the horizontal Adwa Freight OS lockup in app navigation, auth, marketing, invoices, email templates, and exported packets. Use the mark only in constrained spaces such as mobile navigation, favicons, and app launcher surfaces. Maintain clear space equal to the mark's route-node diameter around every logo.
