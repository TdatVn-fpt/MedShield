// apps/web/src/PdfImportControls.tsx — Present PDF page selection and safe import status.
import { useEffect, useRef } from 'react';
import type { usePdfImport } from './usePdfImport';
import './pdfImport.css';

type ImportControls = Pick<
  ReturnType<typeof usePdfImport>,
  'state' | 'cancel' | 'extract' | 'setPage'
>;

/** PdfImportControls displays the current PDF session with keyboard-accessible range controls. */
export default function PdfImportControls({ state, cancel, extract, setPage }: ImportControls) {
  const firstPage = useRef<HTMLInputElement>(null);
  const pages = state.pages;
  useEffect(() => {
    if (pages !== undefined) firstPage.current?.focus({ preventScroll: true });
  }, [pages]);

  if (state.phase === 'idle' && !state.error) return null;

  return (
    <div className="pdf-import">
      {state.phase === 'opening' && <p role="status">Đang mở PDF…</p>}
      {state.phase === 'reading' && <p role="status">Đang trích văn bản…</p>}
      {state.error && <p role="alert">{state.error}</p>}
      {pages !== undefined && (
        <form
          aria-label="Chọn trang PDF"
          noValidate
          onSubmit={(event) => {
            event.preventDefault();
            void extract();
          }}
        >
          <p>PDF có {pages} trang. Chọn tối đa 10 trang mỗi lượt.</p>
          <div className="pdf-import-fields">
            <label>
              Trang đầu
              <input
                ref={firstPage}
                type="number"
                min={1}
                max={pages}
                value={state.first}
                disabled={state.phase === 'reading'}
                onChange={(event) => setPage('first', event.target.value)}
              />
            </label>
            <label>
              Trang cuối
              <input
                type="number"
                min={1}
                max={pages}
                value={state.last}
                disabled={state.phase === 'reading'}
                onChange={(event) => setPage('last', event.target.value)}
              />
            </label>
            <button
              className="secondary-button"
              type="submit"
              disabled={state.phase === 'reading'}
            >
              Trích văn bản
            </button>
          </div>
        </form>
      )}
      {state.phase !== 'idle' && (
        <button className="text-button" type="button" onClick={cancel}>
          Hủy nhập PDF
        </button>
      )}
    </div>
  );
}
