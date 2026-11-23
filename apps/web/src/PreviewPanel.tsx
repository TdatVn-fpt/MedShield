// apps/web/src/PreviewPanel.tsx — Show only the current redacted preview and explicit export approval.
import type { Redaction } from './types';

type Props = {
  preview: Redaction | null;
  busy: boolean;
  approved: boolean;
  onApproved: (value: boolean) => void;
  onExport: (format: 'txt' | 'json') => void;
};

/** PreviewPanel requires a current preview and explicit human review before any download. */
export default function PreviewPanel(props: Props) {
  return (
    <section className="document-panel preview-panel" aria-labelledby="preview-title">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">02 / KẾT QUẢ XEM TRƯỚC</span>
          <h2 id="preview-title">Bản đã che</h2>
        </div>
        <span className={`tag ${props.preview ? 'success-tag' : 'subtle'}`}>
          {props.preview ? 'Đã cập nhật' : 'Chờ phân tích'}
        </span>
      </div>
      <div
        className="preview-content"
        aria-label="Bản đã che"
        aria-live="polite"
        aria-busy={props.busy}
      >
        {props.busy ? (
          <div className="preview-empty">
            <span className="spinner" aria-hidden="true" />
            <h3>Đang xử lý văn bản</h3>
            <p>Kết quả sẽ xuất hiện khi API hoàn tất.</p>
          </div>
        ) : props.preview ? (
          <p className="redacted-text">{props.preview.redacted_text}</p>
        ) : (
          <div className="preview-empty">
            <span className="document-symbol" aria-hidden="true">
              ▤
            </span>
            <h3>Nội dung an toàn hơn để chia sẻ</h3>
            <p>
              Nhập ghi chú, phân tích và rà soát.
              <br />
              Bản che sẽ được hiển thị tại đây.
            </p>
          </div>
        )}
      </div>
      <div className="review-export">
        <label className="approval-label">
          <input
            type="checkbox"
            checked={props.approved}
            disabled={!props.preview || props.busy}
            onChange={(event) => props.onApproved(event.target.checked)}
          />
          <span>Tôi đã rà soát toàn bộ nội dung</span>
        </label>
        <p>Kiểm tra cả thông tin còn sót. Kết quả tự động có thể sai.</p>
        <div className="export-buttons">
          <button
            className="primary-button"
            disabled={!props.preview || !props.approved || props.busy}
            onClick={() => props.onExport('txt')}
          >
            <span aria-hidden="true">↓</span> Tải TXT
          </button>
          <button
            className="secondary-button"
            disabled={!props.preview || !props.approved || props.busy}
            onClick={() => props.onExport('json')}
          >
            Tải JSON
          </button>
        </div>
      </div>
    </section>
  );
}
