// apps/web/e2e/phase-q2-phone-review.spec.ts — Exercise the manual queue for ambiguous phone spans.
import { expect, test } from '@playwright/test';

test('puts a tentative phone first without changing its original offset or edit target', async ({
  page,
}) => {
  const phone = '+84 891 251 661 22';
  const text = `Họ tên: Đặng Thiên Liên; dãy rời ${phone}.`;
  await page.goto('/');
  await page.getByLabel('Văn bản gốc', { exact: true }).fill(text);
  const analyzed = page.waitForResponse((response) => response.url().endsWith('/api/analyze'));
  await page.getByRole('button', { name: 'Phân tích', exact: true }).click();
  const response = await analyzed;
  expect(response.ok()).toBe(true);
  const start = text.indexOf(phone);
  expect((await response.json()).entities).toContainEqual({
    start,
    end: start + phone.length,
    label: 'PHONE',
    source: 'medshield-rules+phone-review',
    score: 0.4,
  });
  const detections = page.getByRole('region', { name: /Các vùng được phát hiện/ });
  await expect(detections.getByRole('status')).toContainText('1 đề xuất');
  await expect(detections.locator('article').first()).toContainText(phone);
  await expect(detections.locator('article').first()).toContainText('Cần kiểm tra');
  await expect(page.getByRole('button', { name: 'Tải TXT' })).toBeDisabled();
  const preview = page.waitForResponse((response) => response.url().endsWith('/api/redact'));
  await detections.getByRole('button', { name: 'Bỏ phát hiện 2' }).click();
  expect((await preview).ok()).toBe(true);
  await expect(detections.getByRole('status')).toHaveCount(0);
  await expect(detections.locator('article')).toContainText('Đặng Thiên Liên');
});
