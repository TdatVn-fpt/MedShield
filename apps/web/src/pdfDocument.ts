// apps/web/src/pdfDocument.ts — Read selected pages locally using a dedicated PDF.js worker.
import { getDocument, GlobalWorkerOptions } from 'pdfjs-dist';
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';
import { MAX_TEXT_POINTS, PdfImportError } from './pdfPolicy';

type Fragment = { text: string; x: number; y: number; width: number };

export type PdfDocument = {
  pageCount: number;
  extract: (first: number, last: number) => Promise<string>;
};

/** formatRows orders fragments by visual row and inserts spaces across column gaps. */
function formatRows(fragments: Fragment[]): string {
  const rows: { baseline: number; fragments: Fragment[] }[] = [];
  fragments.sort((a, b) => a.y - b.y || a.x - b.x);
  for (const fragment of fragments) {
    const row = rows.at(-1);
    if (row && Math.abs(fragment.y - row.baseline) <= 2.5) {
      row.fragments.push(fragment);
    } else {
      rows.push({ baseline: fragment.y, fragments: [fragment] });
    }
  }
  return rows
    .map(({ fragments: items }) => {
      let end = 0;
      let line = '';
      for (const item of items.sort((a, b) => a.x - b.x)) {
        const gap = item.x - end;
        if (line && !/\s$/.test(line) && !/^\s/.test(item.text) && gap > 1) {
          line += gap >= 18 ? '  ' : ' ';
        }
        line += item.text;
        end = item.x + item.width;
      }
      return line.trim();
    })
    .filter(Boolean)
    .join('\n');
}

/** openPdf reads a local file, gives access to pages and releases the worker on abort. */
export async function openPdf(file: File, signal: AbortSignal): Promise<PdfDocument> {
  const data = new Uint8Array(await file.arrayBuffer());
  signal.throwIfAborted();
  if (!new TextDecoder().decode(data.subarray(0, 1024)).includes('%PDF-')) {
    throw new PdfImportError('Tệp được chọn không có định dạng PDF.');
  }
  GlobalWorkerOptions.workerSrc = workerUrl;
  const task = getDocument({ data, stopAtErrors: true, verbosity: 0, useWasm: false });
  const destroy = () => void task.destroy().catch(() => undefined);
  signal.addEventListener('abort', destroy, { once: true });
  try {
    const doc = await task.promise;
    signal.throwIfAborted();
    return {
      pageCount: doc.numPages,
      async extract(first, last) {
        const texts: string[] = [];
        const missing: number[] = [];
        let points = 0;
        for (let n = first; n <= last; n += 1) {
          signal.throwIfAborted();
          const page = await doc.getPage(n);
          try {
            const viewport = page.getViewport({ scale: 1 });
            const { items } = await page.getTextContent();
            const fragments = items.flatMap((item) => {
              if (!('str' in item) || !item.str) return [];
              const [x, y] = viewport.convertToViewportPoint(item.transform[4], item.transform[5]);
              return [{ text: item.str, width: item.width, x, y }];
            });
            const text = formatRows(fragments);
            if (!text.trim()) missing.push(n);
            points += Array.from(text).length + (texts.length > 0 ? 2 : 0);
            if (points > MAX_TEXT_POINTS) {
              throw new PdfImportError('Văn bản vượt 50.000 ký tự. Hãy chọn ít trang hơn.');
            }
            texts.push(text);
          } finally {
            page.cleanup();
          }
        }
        if (missing.length) {
          throw new PdfImportError(
            `Trang ${missing.join(', ')} không có lớp chữ. Hãy chọn khoảng trang khác hoặc dùng TXT sau khi OCR.`,
          );
        }
        return texts.join('\n\n');
      },
    };
  } catch (error) {
    if (!signal.aborted) destroy();
    signal.removeEventListener('abort', destroy);
    throw error;
  }
}
