// apps/web/src/DetectionList.tsx — Locate, relabel and remove individual reviewed entities.
import { LABEL_NAMES, LABELS } from './types';
import type { Entity, Label } from './types';
import { slicePoints } from './unicode';

type Props = {
  text: string;
  entities: Entity[];
  analyzed: boolean;
  onEntities: (entities: Entity[]) => Promise<void>;
  onFocus: (index: number) => void;
};

/** Identify an unanchored phone candidate that needs a manual decision. */
function needsPhoneReview(entity: Entity) {
  return (
    entity.label === 'PHONE' &&
    entity.source === 'medshield-rules+phone-review' &&
    entity.score < 0.5
  );
}

/** DetectionList keeps each machine proposal editable and identifies its true detection source. */
export default function DetectionList(props: Props) {
  const rows = props.entities.map((entity, index) => ({ entity, index }));
  const pending = rows.filter(({ entity }) => needsPhoneReview(entity));
  const confirmed = rows.filter(({ entity }) => !needsPhoneReview(entity));
  return (
    <section className="detections" aria-labelledby="detections-title">
      <div className="section-heading">
        <div>
          <span className="eyebrow">RÀ SOÁT THỦ CÔNG</span>
          <h2 id="detections-title">
            Các vùng được phát hiện <span className="count-badge">{props.entities.length}</span>
          </h2>
        </div>
        <p>Máy đề xuất. Bạn quyết định.</p>
      </div>
      {pending.length > 0 && (
        <p role="status">Cần kiểm tra số điện thoại: {pending.length} đề xuất.</p>
      )}
      {props.entities.length ? (
        <div className="detection-grid">
          {[...pending, ...confirmed].map(({ entity, index }) => (
            <article className="entity-row" key={`${entity.start}:${entity.end}`}>
              <span className={`entity-dot dot-${entity.label}`} aria-hidden="true" />
              <button
                className="entity-value"
                onClick={() => props.onFocus(index)}
                aria-label={`Định vị phát hiện ${index + 1}`}
              >
                <strong>{slicePoints(props.text, entity.start, entity.end)}</strong>
                {needsPhoneReview(entity) && <span>Cần kiểm tra số điện thoại</span>}
                <span>
                  {entity.source} · [{entity.start}, {entity.end})
                </span>
              </button>
              <select
                aria-label={`Nhãn phát hiện ${index + 1}`}
                value={entity.label}
                onChange={(event) => {
                  const next = props.entities.map((item, itemIndex) =>
                    itemIndex === index
                      ? { ...item, label: event.target.value as Label, source: 'manual', score: 1 }
                      : item,
                  );
                  void props.onEntities(next);
                }}
              >
                {LABELS.map((label) => (
                  <option key={label} value={label}>
                    {label} · {LABEL_NAMES[label]}
                  </option>
                ))}
              </select>
              <button
                className="remove-button"
                aria-label={`Bỏ phát hiện ${index + 1}`}
                title="Bỏ vùng che nhầm"
                onClick={() =>
                  void props.onEntities(
                    props.entities.filter((_, itemIndex) => itemIndex !== index),
                  )
                }
              >
                ×
              </button>
            </article>
          ))}
        </div>
      ) : (
        <div className="empty-detections">
          {props.analyzed
            ? 'Không có vùng được chọn. Bạn vẫn cần đọc lại toàn bộ bản gốc trước khi xuất.'
            : 'Các phát hiện và công cụ chỉnh sửa sẽ xuất hiện sau khi phân tích.'}
        </div>
      )}
      <div className="label-legend">
        {LABELS.map((label) => (
          <span key={label}>
            <i className={`entity-dot dot-${label}`} aria-hidden="true" />
            <b>{label}</b> {LABEL_NAMES[label]}
          </span>
        ))}
      </div>
    </section>
  );
}
