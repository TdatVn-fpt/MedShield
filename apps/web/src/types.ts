// apps/web/src/types.ts — Shared API types and Vietnamese label names.
export const LABELS = ['NAME', 'DOB', 'PHONE', 'ID', 'ADDR'] as const;
export type Label = (typeof LABELS)[number];
export type Entity = {
  start: number;
  end: number;
  label: Label;
  source: string;
  score: number;
};
export type Engine = {
  name: string;
  status: 'available' | 'unavailable';
  mode: 'rules' | 'ner' | 'hybrid';
  language: 'vi' | 'en';
};
export type Redaction = {
  redacted_text: string;
  metadata: {
    entity_count: number;
    counts_by_label: Record<Label, number>;
    offset_unit: 'unicode_code_point';
  };
};
export type Analysis = {
  entities: Entity[];
  redacted_text: string;
  engine: Engine;
};
export const LABEL_NAMES: Record<Label, string> = {
  NAME: 'Họ và tên',
  DOB: 'Ngày sinh',
  PHONE: 'Điện thoại',
  ID: 'Mã định danh',
  ADDR: 'Địa chỉ',
};
export const EXAMPLE =
  'Người bệnh Mai An, sinh ngày 03/02/1995, mã BN-00071.\n' +
  'Điện thoại: 0901234567. Địa chỉ: 12 đường Sen, phường Bình An.\n\n' +
  'Mai An đến khám vì ho khan ba ngày. Hẹn khám lại 18/12.\n' +
  'Ghi chú này hoàn toàn là dữ liệu giả lập.';
