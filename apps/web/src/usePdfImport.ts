// apps/web/src/usePdfImport.ts — Run an abortable PDF selection and extraction session.
import { useEffect, useRef, useState } from 'react';
import type { PdfDocument } from './pdfDocument';
import { MAX_PDF_BYTES, MAX_PDF_PAGES, PdfImportError } from './pdfPolicy';

type ImportSession = { abort: AbortController; doc?: PdfDocument; extracting?: boolean };
type ImportState = {
  phase: 'idle' | 'opening' | 'ready' | 'reading';
  pages?: number;
  first?: string;
  last?: string;
  error?: string;
};

/** errorMessage filters out parser messages that can carry information from the document. */
function errorMessage(error: unknown): string {
  if (error instanceof PdfImportError) return error.message;
  if (error instanceof Error && error.name === 'PasswordException') {
    return 'PDF yêu cầu mật khẩu. Hãy dùng bản có thể mở trực tiếp.';
  }
  return 'Không đọc được PDF. Tệp có thể bị hỏng hoặc không được hỗ trợ.';
}

/** usePdfImport keeps a single local worker session and ignores results from stale inputs. */
export function usePdfImport(onText: (text: string) => void) {
  const current = useRef<ImportSession | null>(null);
  const [state, setState] = useState<ImportState>({ phase: 'idle' });

  useEffect(() => {
    const session = current;
    return () => session.current?.abort.abort();
  }, []);

  /** cancel releases local resources and returns to the original note. */
  function cancel(): void {
    current.current?.abort.abort();
    current.current = null;
    setState({ phase: 'idle' });
  }

  /** start validates size and opens the newest file without extracting pages yet. */
  async function start(file: File): Promise<void> {
    cancel();
    if (file.size > MAX_PDF_BYTES) {
      setState({ phase: 'idle', error: 'PDF vượt 10 MiB. Hãy chọn tệp nhỏ hơn.' });
      return;
    }
    const session: ImportSession = { abort: new AbortController() };
    current.current = session;
    const { signal } = session.abort;
    setState({ phase: 'opening' });
    try {
      const { openPdf } = await import('./pdfDocument');
      if (signal.aborted) return;
      session.doc = await openPdf(file, signal);
      if (signal.aborted) return;
      const { pageCount } = session.doc;
      const last = pageCount > MAX_PDF_PAGES ? 1 : pageCount;
      setState({ phase: 'ready', pages: pageCount, first: '1', last: String(last) });
    } catch (error) {
      if (signal.aborted) return;
      cancel();
      setState({ phase: 'idle', error: errorMessage(error) });
    }
  }

  /** setPage updates the chosen inclusive page range, keeping empty edits visible. */
  function setPage(which: 'first' | 'last', page: string): void {
    setState((old) => ({ ...old, [which]: page, error: undefined }));
  }

  /** extract validates the page range, then applies only complete, current text. */
  async function extract(): Promise<void> {
    const session = current.current;
    if (!session?.doc || session.extracting || state.phase !== 'ready') return;
    const first = Number(state.first);
    const last = Number(state.last);
    if (
      !Number.isInteger(first) ||
      !Number.isInteger(last) ||
      first < 1 ||
      last < first ||
      last > session.doc.pageCount
    ) {
      setState({ ...state, error: 'Chọn khoảng trang hợp lệ theo số trang của PDF.' });
      return;
    }
    if (last - first + 1 > MAX_PDF_PAGES) {
      setState({ ...state, error: 'Mỗi lượt chỉ được chọn tối đa 10 trang.' });
      return;
    }
    session.extracting = true;
    setState({ ...state, phase: 'reading', error: undefined });
    try {
      const text = await session.doc.extract(first, last);
      if (session.abort.signal.aborted) return;
      cancel();
      onText(text);
    } catch (error) {
      if (session.abort.signal.aborted) return;
      setState({ ...state, error: errorMessage(error) });
    } finally {
      session.extracting = false;
    }
  }

  return { state, start, cancel, extract, setPage };
}
