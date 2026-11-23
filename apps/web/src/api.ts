// apps/web/src/api.ts — In-memory API requests and safe result downloads.
/** requestJson sends a JSON request and returns its typed response without persisting input. */
export async function requestJson<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method: body === undefined ? 'GET' : 'POST',
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: 'no-store',
  }).catch(() => {
    throw new Error('Không kết nối được API. Hãy kiểm tra máy chủ rồi thử lại.');
  });
  const value = await response.json().catch(() => {
    throw new Error('API chưa trả kết quả hợp lệ. Hãy kiểm tra máy chủ rồi thử lại.');
  });
  if (!response.ok) {
    throw new Error(
      response.status === 503
        ? 'Engine đã chọn chưa khả dụng. Hãy kiểm tra trạng thái hoặc chọn Quy tắc.'
        : value.error?.message || 'Không thể xử lý yêu cầu. Vui lòng thử lại.',
    );
  }
  return value as T;
}

/** downloadResult downloads only the approved redacted payload, never entity originals. */
export function downloadResult(content: string, format: 'txt' | 'json'): void {
  const blob = new Blob([content], {
    type: format === 'txt' ? 'text/plain;charset=utf-8' : 'application/json;charset=utf-8',
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `medshield-da-ra-soat.${format}`;
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
