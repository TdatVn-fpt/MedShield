// apps/web/src/unicode.ts — Preserve API codepoint offsets across browser selections.
/** slicePoints extracts a half-open codepoint span without changing Unicode normalization. */
export function slicePoints(text: string, start: number, end: number): string {
  return Array.from(text).slice(start, end).join('');
}

/** selectedSpan maps a selection inside the source element to half-open codepoint offsets. */
export function selectedSpan(container: HTMLElement): { start: number; end: number } | null {
  const selection = window.getSelection();
  if (!selection || selection.rangeCount === 0 || selection.isCollapsed) return null;
  const range = selection.getRangeAt(0);
  if (!container.contains(range.startContainer) || !container.contains(range.endContainer)) {
    return null;
  }
  const before = range.cloneRange();
  before.selectNodeContents(container);
  before.setEnd(range.startContainer, range.startOffset);
  const through = range.cloneRange();
  through.selectNodeContents(container);
  through.setEnd(range.endContainer, range.endOffset);
  const original = container.textContent || '';
  const startUtf16 = before.toString().length;
  const endUtf16 = through.toString().length;
  // A DOM Range can be constructed between a surrogate pair; never emit such a boundary.
  for (const boundary of [startUtf16, endUtf16]) {
    const previous = original.charCodeAt(boundary - 1);
    const next = original.charCodeAt(boundary);
    if (previous >= 0xd800 && previous <= 0xdbff && next >= 0xdc00 && next <= 0xdfff) {
      return null;
    }
  }
  const start = Array.from(before.toString()).length;
  const end = Array.from(through.toString()).length;
  return end > start ? { start, end } : null;
}
