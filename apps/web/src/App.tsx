// apps/web/src/App.tsx — Vietnamese review desk connecting original text to the real API.
import { useEffect, useState } from 'react';
import { requestJson } from './api';
import DetectionList from './DetectionList';
import PreviewPanel from './PreviewPanel';
import SourcePanel from './SourcePanel';
import { useReview } from './useReview';
import type { Engine } from './types';
import './review.css';
import './results.css';
import './responsive.css';

/** App renders a local-only review workspace with truthful engine readiness. */
export default function App() {
  const review = useReview();
  const [editing, setEditing] = useState(true);
  const [focused, setFocused] = useState<number | null>(null);
  const [page, setPage] = useState<'review' | 'evaluation' | 'how'>('review');
  const [engines, setEngines] = useState<Engine[] | null>(null);
  const [evaluationStatus, setEvaluationStatus] = useState('Đang đọc kết quả từ API…');

  useEffect(() => {
    let active = true;
    requestJson<{ engines: Engine[] }>('/health').then(
      (result) => {
        if (active) setEngines(result.engines);
      },
      () => {
        if (active) setEngines([]);
      },
    );
    return () => {
      active = false;
    };
  }, []);

  /** openEvaluation fetches artifact availability without presenting invented metrics. */
  function openEvaluation(): void {
    setPage('evaluation');
    requestJson<{ status: string; reason?: string }>('/api/evaluation').then(
      (result) =>
        setEvaluationStatus(
          result.status === 'available'
            ? 'Đã có artifact đánh giá. Bảng kết quả sẽ được tích hợp tại chặng đánh giá G3.'
            : result.reason || 'Chưa có kết quả đánh giá.',
        ),
      () => setEvaluationStatus('Chưa kết nối được API đánh giá.'),
    );
  }

  /** locateEntity exposes the selected mark in the original document for keyboard review. */
  function locateEntity(index: number): void {
    setEditing(false);
    setFocused(index);
    window.requestAnimationFrame(() => {
      const mark = document.getElementById(`entity-${index}`);
      mark?.focus({ preventScroll: true });
      mark?.scrollIntoView({ behavior: 'auto', block: 'center' });
    });
  }

  const apiReady = engines !== null && engines.length > 0;
  const count = Array.from(review.text).length;
  return (
    <div className="app-shell">
      <header className="site-header">
        <a
          className="brand"
          href="#"
          onClick={(event) => {
            event.preventDefault();
            setPage('review');
          }}
          aria-label="MedShield — trang rà soát"
        >
          <svg viewBox="0 0 40 44" aria-hidden="true">
            <path d="M20 2 36 8v13c0 10-9 17-16 21C13 38 4 31 4 21V8Z" fill="currentColor" />
            <path d="M18 12h4v6h6v4h-6v6h-4v-6h-6v-4h6Z" fill="white" />
          </svg>
          <span>
            Med<span className="brand-light">Shield</span>
            <small>KHÔNG GIAN RÀ SOÁT Y TẾ</small>
          </span>
        </a>
        <nav aria-label="Điều hướng chính">
          <button
            className={page === 'review' ? 'nav-active' : ''}
            onClick={() => setPage('review')}
          >
            Bàn rà soát
          </button>
          <button className={page === 'evaluation' ? 'nav-active' : ''} onClick={openEvaluation}>
            Thực nghiệm
          </button>
          <button className={page === 'how' ? 'nav-active' : ''} onClick={() => setPage('how')}>
            Cách hoạt động
          </button>
        </nav>
        <span className="local-status">
          <i aria-hidden="true" /> Xử lý cục bộ
        </span>
      </header>
      <main>
        {page === 'review' ? (
          <>
            <div className="workspace-intro">
              <div>
                <span className="eyebrow">MEDSHIELD / BÀN RÀ SOÁT</span>
                <h1>
                  Giữ điều cần biết.
                  <br className="mobile-break" /> Che điều riêng tư.
                </h1>
                <p>Nhận diện định danh trong ghi chú y tế, rà soát và chuẩn bị bản chia sẻ.</p>
              </div>
              <div className="privacy-note">
                <span aria-hidden="true">◇</span>
                <p>
                  <strong>Văn bản ở trong phiên này</strong>
                  <br />
                  Không lưu lịch sử hay nội dung hồ sơ.
                </p>
              </div>
            </div>
            <ol className="workflow">
              <li className="step-active">
                <b>1</b> Nhập văn bản
              </li>
              <li>
                <b>2</b> Phân tích & rà soát
              </li>
              <li>
                <b>3</b> Xác nhận & xuất
              </li>
            </ol>
            <section className="analysis-toolbar" aria-label="Cấu hình phân tích">
              <div className="engine-controls">
                <label>
                  Ngôn ngữ
                  <select
                    value={review.language}
                    onChange={(event) =>
                      review.changeConfiguration(event.target.value as 'vi' | 'en', review.mode)
                    }
                  >
                    <option value="vi">Tiếng Việt</option>
                    <option value="en">Tiếng Anh</option>
                  </select>
                </label>
                <label>
                  Phương pháp
                  <select
                    value={review.mode}
                    onChange={(event) =>
                      review.changeConfiguration(
                        review.language,
                        event.target.value as 'rules' | 'ner' | 'hybrid',
                      )
                    }
                  >
                    <option value="rules">Quy tắc · baseline</option>
                    <option value="ner">NER · mô hình học</option>
                    <option value="hybrid">Kết hợp · hybrid</option>
                  </select>
                </label>
              </div>
              <div className="analysis-action">
                <span className={`api-status ${apiReady ? 'is-ready' : ''}`}>
                  {engines === null
                    ? 'Đang kiểm tra API'
                    : apiReady
                      ? 'API đã kết nối'
                      : 'API chưa khả dụng'}
                </span>
                <button
                  className="primary-button analyze-button"
                  disabled={!review.text.trim() || count > 50000 || review.busy}
                  onClick={async () => {
                    if (await review.analyze()) {
                      setEditing(false);
                      setFocused(null);
                    }
                  }}
                >
                  <span aria-hidden="true">✦</span> {review.busy ? 'Đang xử lý…' : 'Phân tích'}
                </button>
              </div>
            </section>
            {review.error && (
              <div className="error-banner" role="alert">
                {review.error}
              </div>
            )}
            {count > 50000 && (
              <div className="error-banner" role="alert">
                Văn bản vượt giới hạn 50.000 ký tự.
              </div>
            )}
            <div className="document-grid">
              <SourcePanel
                text={review.text}
                entities={review.entities}
                analyzed={review.analyzed}
                editing={editing}
                focused={focused}
                onEditing={setEditing}
                onText={review.changeText}
                onEntities={review.changeEntities}
                onError={review.reportError}
              />
              <PreviewPanel
                preview={review.preview}
                busy={review.busy}
                approved={review.approved}
                onApproved={review.setApproved}
                onExport={review.exportFile}
              />
            </div>
            <DetectionList
              text={review.text}
              entities={review.entities}
              analyzed={review.analyzed}
              onEntities={review.changeEntities}
              onFocus={locateEntity}
            />
            {review.engine && (
              <p className="engine-footnote">
                Engine đã chạy: <strong>{review.engine.name}</strong> · {review.engine.mode} ·{' '}
                {review.engine.language} · Vị trí theo Unicode code point.
              </p>
            )}
          </>
        ) : (
          <section className="information-page">
            <span className="eyebrow">
              MEDSHIELD / {page === 'evaluation' ? 'BẰNG CHỨNG THỰC NGHIỆM' : 'TÌM HIỂU QUY TRÌNH'}
            </span>
            <h1>
              {page === 'evaluation'
                ? 'Kết quả được đo, có thể kiểm tra lại.'
                : 'Từ ghi chú đến bản đã rà soát.'}
            </h1>
            <p>
              {page === 'evaluation'
                ? evaluationStatus
                : 'Nhận diện vùng định danh → người dùng rà soát và chỉnh sửa → thay vùng đã chọn bằng ký hiệu → xác nhận và xuất.'}
            </p>
            <button className="secondary-button" onClick={() => setPage('review')}>
              Quay lại bàn rà soát
            </button>
          </section>
        )}
      </main>
      <footer className="site-footer">
        <span>
          MedShield <b>·</b> Samsung Innovation Campus / AI-NIC4
        </span>
        <span>
          Nguyễn Tiến Đạt <b>·</b> Demo dùng dữ liệu giả lập
        </span>
      </footer>
    </div>
  );
}
