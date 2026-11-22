// apps/web/src/SourcePanel.tsx — Edit original text and select codepoint spans for review.
import { useEffect, useRef, useState } from 'react';
import PdfImportControls from './PdfImportControls';
import { EXAMPLE, LABEL_NAMES, LABELS } from './types';
import type { Entity, Label } from './types';
import { selectedSpan, slicePoints } from './unicode';
import { usePdfImport } from './usePdfImport';

type Props = {
  text: string;
  entities: Entity[];
  analyzed: boolean;
  editing: boolean;
  focused: number | null;
  onEditing: (value: boolean) => void;
  onText: (value: string) => void;
  onEntities: (value: Entity[]) => Promise<void>;
  onError: (message: string) => void;
};

/** SourcePanel presents original text and adds user-selected spans without changing Unicode. */
export default function SourcePanel(props: Props) {
  const source = useRef<HTMLDivElement>(null);
  const editor = useRef<HTMLTextAreaElement>(null);
  const inputVersion = useRef(0);
  const [selection, setSelection] = useState<{ start: number; end: number } | null>(null);
  const [label, setLabel] = useState<Label>('NAME');
  const pdfImport = usePdfImport((text) => {
    props.onText(text);
    props.onEditing(true);
    setSelection(null);
    requestAnimationFrame(() => editor.current?.focus());
  });
  useEffect(() => {
    const version = inputVersion;
    return () => {
      version.current += 1;
    };
  }, []);
  const points = Array.from(props.text);
  const marks = [];
  let position = 0;
  for (const [index, entity] of props.entities.entries()) {
    marks.push(points.slice(position, entity.start).join(''));
    marks.push(
      <mark
        key={`${entity.start}:${entity.end}`}
        id={`entity-${index}`}
        tabIndex={-1}
        className={`mark-${entity.label} ${props.focused === index ? 'focused-mark' : ''}`}
        title={`${entity.label} · ${LABEL_NAMES[entity.label]}`}
      >
        {points.slice(entity.start, entity.end).join('')}
      </mark>,
    );
    position = entity.end;
  }
  marks.push(points.slice(position).join(''));

  /** captureSelection records only non-empty selections inside the highlighted original. */
  function captureSelection(): void {
    setSelection(source.current ? selectedSpan(source.current) : null);
  }

  /** addSelection rejects overlaps and sends the user's exact chosen span for a new preview. */
  function addSelection(): void {
    if (!selection) return;
    if (props.entities.some((item) => selection.start < item.end && selection.end > item.start)) {
      props.onError('Vùng đã chọn chồng lên một phát hiện. Hãy bỏ phát hiện đó trước.');
      return;
    }
    void props.onEntities(
      [...props.entities, { ...selection, label, source: 'manual', score: 1 }].sort(
        (left, right) => left.start - right.start,
      ),
    );
    setSelection(null);
    window.getSelection()?.removeAllRanges();
  }

  /** uploadText reads strict UTF-8 and applies only the latest input action. */
  async function uploadText(file: File | undefined): Promise<void> {
    if (!file) return;
    pdfImport.cancel();
    const version = ++inputVersion.current;
    if (file.size > 200004) {
      props.onError('Tệp quá lớn. Vui lòng dùng TXT tối đa 50.000 ký tự.');
      return;
    }
    try {
      const bytes = await file.arrayBuffer();
      if (inputVersion.current !== version) return;
      // TextDecoder consumes the first UTF-8 BOM before positions are counted.
      const text = new TextDecoder('utf-8', { fatal: true }).decode(bytes);
      if (Array.from(text).length > 50000) {
        props.onError('Văn bản vượt giới hạn 50.000 ký tự.');
        return;
      }
      props.onText(text);
      props.onEditing(true);
      setSelection(null);
    } catch {
      if (inputVersion.current === version) {
        props.onError('Không đọc được TXT UTF-8. Hãy lưu tệp bằng mã hóa UTF-8 rồi thử lại.');
      }
    }
  }

  return (
    <section className="document-panel source-panel" aria-labelledby="source-title">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">01 / VĂN BẢN ĐẦU VÀO</span>
          <h2 id="source-title">Bản gốc</h2>
        </div>
        <span className="tag subtle">Chỉ trong bộ nhớ</span>
      </div>
      <div className="source-tools">
        <button
          className="text-button"
          onClick={() => {
            inputVersion.current += 1;
            pdfImport.cancel();
            props.onText(EXAMPLE);
            props.onEditing(true);
            setSelection(null);
          }}
        >
          Dùng ví dụ giả lập <span aria-hidden="true">↗</span>
        </button>
        <label className="file-button">
          Tải TXT lên
          <input
            type="file"
            accept=".txt,text/plain"
            aria-label="Tải tệp TXT UTF-8"
            onChange={(event) => {
              void uploadText(event.target.files?.[0]);
              event.target.value = '';
            }}
          />
        </label>
        <label className="file-button">
          Nhập PDF
          <input
            type="file"
            accept=".pdf,application/pdf"
            aria-label="Nhập PDF"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) {
                inputVersion.current += 1;
                void pdfImport.start(file);
              }
              event.target.value = '';
            }}
          />
        </label>
      </div>
      <PdfImportControls {...pdfImport} />
      {props.editing || !props.analyzed ? (
        <textarea
          ref={editor}
          className="source-input"
          aria-label="Văn bản gốc"
          placeholder={'Dán ghi chú y tế vào đây…\n\nHoặc chọn “Dùng ví dụ giả lập” để bắt đầu.'}
          value={props.text}
          spellCheck={false}
          onChange={(event) => {
            inputVersion.current += 1;
            pdfImport.cancel();
            props.onText(event.target.value);
            setSelection(null);
          }}
        />
      ) : (
        <>
          <div
            ref={source}
            className="marked-source"
            aria-label="Văn bản gốc có đánh dấu"
            tabIndex={0}
            onMouseUp={captureSelection}
            onKeyUp={captureSelection}
          >
            {marks}
          </div>
          <button
            className="text-button edit-original"
            onClick={() => {
              props.onEditing(true);
              setSelection(null);
            }}
            aria-label="Sửa văn bản"
          >
            Sửa văn bản gốc
          </button>
        </>
      )}
      <div className="document-footer">
        <span>{points.length.toLocaleString('vi-VN')} / 50.000 ký tự</span>
        <span>TXT UTF-8 · PDF có chữ</span>
      </div>
      {props.analyzed && !props.editing && (
        <div className="manual-add">
          <p>
            {selection ? (
              <>
                Đã chọn: <strong>{slicePoints(props.text, selection.start, selection.end)}</strong>
              </>
            ) : (
              'Bôi chọn đoạn còn sót trong bản gốc để thêm vùng che.'
            )}
          </p>
          <div className="manual-controls">
            <select
              aria-label="Nhãn vùng che mới"
              value={label}
              onChange={(event) => setLabel(event.target.value as Label)}
            >
              {LABELS.map((value) => (
                <option key={value} value={value}>
                  {value} · {LABEL_NAMES[value]}
                </option>
              ))}
            </select>
            <button
              className="secondary-button"
              aria-label="Thêm vùng che"
              disabled={!selection}
              onClick={addSelection}
            >
              + Thêm vùng che
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
