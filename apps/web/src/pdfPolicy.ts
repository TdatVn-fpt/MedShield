// apps/web/src/pdfPolicy.ts — Shared input limits and user-safe PDF import errors.
export const MAX_PDF_BYTES = 10 * 1024 * 1024;
export const MAX_PDF_PAGES = 10;
export const MAX_TEXT_POINTS = 50_000;

export class PdfImportError extends Error {}
