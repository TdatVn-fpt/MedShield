// apps/web/src/EvaluationPage.tsx — Display the executed evaluation artifact and its provenance.
import { useEffect, useState } from 'react';
import { requestJson } from './api';
import './evaluation.css';

type Metrics = {
  tp: number;
  fp: number;
  fn: number;
  precision: number;
  recall: number;
  f1: number;
  support: number;
};

type Result = {
  language: 'vi' | 'en';
  method: string;
  status: 'available' | 'unavailable';
  reason?: string;
  notes?: number;
  gold_entities?: number;
  micro?: Metrics;
  by_label?: Record<string, Metrics>;
  notes_with_fn?: number;
  examples?: { note_id: string; kind: string; label?: string; text?: string }[];
};

type Dataset = {
  source?: string;
  train_notes?: number;
  validation_notes?: number;
  test_notes?: number;
  participant_reviewed_count?: number;
};

type Evaluation = {
  datasets?: Partial<Record<'vi' | 'en', Dataset>>;
  results: Result[];
};

type EvaluationResponse =
  { status: 'available'; evaluation: Evaluation } | { status: 'unavailable'; reason: string };

const methodNames: Record<string, string> = {
  rules: 'Quy tắc',
  ner: 'NER · CRF',
  hybrid: 'Kết hợp',
  presidio: 'Presidio',
  philter: 'Philter UCSF',
  pydeid: 'GEMINI pyDeid',
};

const percentFormat = new Intl.NumberFormat('vi-VN', {
  style: 'percent',
  maximumFractionDigits: 1,
});

/** MetricTable renders the original micro and per-label counts with percentages. */
function MetricTable({ result }: { result: Result & { micro: Metrics } }) {
  const rows = [['Micro', result.micro] as const, ...Object.entries(result.by_label ?? {})];
  return (
    <div className="metric-scroll" tabIndex={0} aria-label="Bảng số liệu có thể cuộn ngang">
      <table className="metric-table" aria-label={methodNames[result.method] ?? result.method}>
        <thead>
          <tr>
            {['Nhãn', 'Support', 'TP', 'FP', 'FN', 'Precision', 'Recall', 'F1'].map((column) => (
              <th key={column} scope="col">
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map(([label, metrics]) => (
            <tr key={label}>
              <th scope="row">{label}</th>
              <td>{metrics.support}</td>
              <td>{metrics.tp}</td>
              <td>{metrics.fp}</td>
              <td>{metrics.fn}</td>
              <td>{percentFormat.format(metrics.precision)}</td>
              <td>{percentFormat.format(metrics.recall)}</td>
              <td>{percentFormat.format(metrics.f1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** MethodResult shows measured counts, misses and synthetic examples for one engine. */
function MethodResult({ result }: { result: Result }) {
  const name = methodNames[result.method] ?? result.method;
  if (result.status !== 'available' || !result.micro) {
    return (
      <article className="metric-card">
        <h3>{name}</h3>
        <p>{result.reason || 'Chưa có kết quả chạy cho phương pháp này.'}</p>
      </article>
    );
  }
  return (
    <article className="metric-card">
      <h3>{name}</h3>
      <p data-testid="method-corpus">
        {result.notes} ghi chú · {result.gold_entities} vùng gán nhãn · {result.notes_with_fn} ghi
        chú còn ít nhất một phần bị bỏ sót
      </p>
      <MetricTable result={{ ...result, micro: result.micro }} />
      {Boolean(result.examples?.length) && (
        <details>
          <summary>Ví dụ lỗi từ dữ liệu giả lập</summary>
          <ul>
            {result.examples?.map((example, index) => (
              <li key={`${example.note_id}-${index}`}>
                <strong>{example.kind.toUpperCase() === 'FN' ? 'Bỏ sót' : 'Che nhầm'}</strong>{' '}
                {example.label && `(${example.label})`} · {example.note_id} ·{' '}
                <span>{example.text}</span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </article>
  );
}

/** EvaluationPage fetches measured results while mounted and displays API availability. */
export default function EvaluationPage({ onBack }: { onBack: () => void }) {
  const [response, setResponse] = useState<EvaluationResponse | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    requestJson<EvaluationResponse>('/api/evaluation').then(
      (result) => {
        if (active) setResponse(result);
      },
      () => {
        if (active) setError('Chưa kết nối được API đánh giá.');
      },
    );
    return () => {
      active = false;
    };
  }, []);

  return (
    <section className="evaluation-page" aria-labelledby="evaluation-title">
      <header>
        <h1 id="evaluation-title">Kết quả thực nghiệm</h1>
        <p>Điểm được đo trên ghi chú giả lập, trước khi người dùng sửa kết quả.</p>
      </header>
      {error && <p role="alert">{error}</p>}
      {!error && !response && <p role="status">Đang đọc kết quả từ API…</p>}
      {response?.status === 'unavailable' && <p role="status">{response.reason}</p>}
      {response?.status === 'available' &&
        (['vi', 'en'] as const).map((language) => {
          const vietnamese = language === 'vi';
          const dataset = response.evaluation.datasets?.[language];
          const results = response.evaluation.results.filter((item) => item.language === language);
          return (
            <section key={language} className="metric-section">
              <h2>{vietnamese ? 'Tiếng Việt' : 'Đối chứng tiếng Anh'}</h2>
              <p>
                {vietnamese
                  ? 'Khớp chính xác vị trí bắt đầu, vị trí kết thúc và nhãn. Mục tiêu F1 từng nhãn là 85%.'
                  : 'Đo các ký tự cần che ngoài khoảng trắng. Support là số ký tự được gán cần che.'}
              </p>
              <p>{dataset?.source ?? 'Nguồn dữ liệu là bộ ghi chú giả lập MedShield.'}</p>
              {vietnamese && dataset?.train_notes !== undefined && (
                <p>
                  {dataset.train_notes} train · {dataset.validation_notes} validation ·{' '}
                  {dataset.test_notes} test · {dataset.participant_reviewed_count} ghi chú do người
                  học trực tiếp rà soát
                </p>
              )}
              {results.length ? (
                results.map((result) => <MethodResult key={result.method} result={result} />)
              ) : (
                <p>Chưa có kết quả đánh giá cho ngôn ngữ này.</p>
              )}
            </section>
          );
        })}
      <button className="secondary-button" onClick={onBack}>
        Quay lại bàn rà soát
      </button>
    </section>
  );
}
