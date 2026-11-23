// apps/web/src/EvaluationProvenance.tsx — Expose experiment revisions and commands supplied by the API.
type DevelopmentSplit = { family_ids?: string[] };

export type EvaluationMetadata = {
  vi?: {
    test_manifest?: {
      dataset_revision?: string;
      digest?: { value?: string };
      families?: { family_id: string }[];
    };
    development_manifest?: {
      revision?: string;
      seed?: number;
      splits?: Record<string, DevelopmentSplit>;
    };
    model?: { revision?: string; labels?: string[]; training_config?: Record<string, unknown> };
    reproduce?: string;
    f1_target?: number;
  };
  en?: { dataset?: { revision?: string; family_ids?: string[] }; reproduce?: string[] };
  merge_command?: string;
};

/** EvaluationProvenance shows split families, versions, configuration and rerun commands. */
export default function EvaluationProvenance({ metadata }: { metadata: EvaluationMetadata }) {
  const vi = metadata.vi;
  const en = metadata.en;
  const commands = [vi?.reproduce, ...(en?.reproduce ?? []), metadata.merge_command].filter(
    Boolean,
  );
  return (
    <details className="metric-card metric-provenance">
      <summary>Nguồn và cách tái tạo</summary>
      {vi && (
        <>
          <p>Seed train/validation {vi.development_manifest?.seed ?? '—'}</p>
          <p>Revision train/validation {vi.development_manifest?.revision ?? '—'}</p>
          <p>Revision test tiếng Việt {vi.test_manifest?.dataset_revision ?? '—'}</p>
          <p>SHA-256 test tiếng Việt {vi.test_manifest?.digest?.value ?? '—'}</p>
          <p>Revision mô hình CRF {vi.model?.revision ?? '—'}</p>
          <p>Nhãn CRF {vi.model?.labels?.join(', ') ?? '—'}</p>
          {Object.entries(vi.development_manifest?.splits ?? {}).map(([split, data]) => (
            <p key={split}>
              Họ {split} · {data.family_ids?.join(', ')}
            </p>
          ))}
          <p>Họ test · {vi.test_manifest?.families?.map((item) => item.family_id).join(', ')}</p>
          {vi.model?.training_config && (
            <p>
              Cấu hình CRF <code>{JSON.stringify(vi.model.training_config)}</code>
            </p>
          )}
        </>
      )}
      {en?.dataset && (
        <p>
          Revision đối chứng tiếng Anh {en.dataset.revision} · {en.dataset.family_ids?.length} họ
        </p>
      )}
      {commands.length > 0 && <pre aria-label="Lệnh tái tạo">{commands.join('\n')}</pre>}
    </details>
  );
}
