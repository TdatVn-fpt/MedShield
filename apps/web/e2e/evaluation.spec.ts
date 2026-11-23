// apps/web/e2e/evaluation.spec.ts — Compare the experiment dashboard with the real API.
import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';

type Metrics = {
  support: number;
  tp: number;
  fp: number;
  fn: number;
  precision: number;
  recall: number;
  f1: number;
};

type Method = {
  language: 'vi' | 'en';
  method: string;
  status: 'available' | 'unavailable';
  reason?: string;
  notes?: number;
  gold_entities?: number;
  notes_with_fn?: number;
  micro?: Metrics;
  by_label?: Record<string, Metrics>;
  examples?: { note_id: string; text?: string }[];
};

const methodNames: Record<string, string> = {
  rules: 'Quy tắc',
  ner: 'NER · CRF',
  hybrid: 'Kết hợp',
  presidio: 'Presidio',
  philter: 'Philter UCSF',
  pydeid: 'GEMINI pyDeid',
};

/** metricCells converts one API metric row to the strings presented in the Vietnamese UI. */
function metricCells({ support, tp, fp, fn, precision, recall, f1 }: Metrics): string[] {
  const percent = new Intl.NumberFormat('vi-VN', { style: 'percent', maximumFractionDigits: 1 });
  return [
    support,
    tp,
    fp,
    fn,
    percent.format(precision),
    percent.format(recall),
    percent.format(f1),
  ].map(String);
}

/** openEvaluation opens the dashboard and returns the actual GET response received by Chromium. */
async function openEvaluation(page: Page) {
  const received = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === '/api/evaluation' &&
      response.request().method() === 'GET',
  );
  await page.getByRole('button', { name: 'Thực nghiệm', exact: true }).click();
  return received;
}

for (const width of [390, 1440]) {
  test(`dashboard matches the live evaluation artifact at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    const pageErrors: Error[] = [];
    page.on('pageerror', (error) => pageErrors.push(error));
    await page.goto('/');
    const response = await openEvaluation(page);
    expect(response.status()).toBe(200);
    const { status, evaluation } = await response.json();
    expect(status, 'Publish the merged evaluation artifact before running this check.').toBe(
      'available',
    );
    const results: Method[] = evaluation.results;
    expect(results.map(({ language, method }) => `${language}/${method}`).sort()).toEqual([
      'en/philter',
      'en/presidio',
      'en/pydeid',
      'vi/hybrid',
      'vi/ner',
      'vi/rules',
    ]);
    for (const result of results) {
      const section = page.locator('.metric-section').filter({
        has: page.getByRole('heading', {
          name: result.language === 'vi' ? 'Tiếng Việt' : 'Đối chứng tiếng Anh',
          level: 2,
          exact: true,
        }),
      });
      const name = methodNames[result.method];
      const card = section.getByRole('article').filter({
        has: page.getByRole('heading', { name, level: 3, exact: true }),
      });
      const table = card.getByRole('table', { name, exact: true });
      await expect(card).toBeVisible();
      if (result.status === 'unavailable') {
        if (result.reason)
          await expect(card.getByText(result.reason, { exact: true })).toBeVisible();
        await expect(table).toHaveCount(0);
        continue;
      }
      await expect(card.getByTestId('method-corpus')).toHaveText(
        `${result.notes} ghi chú · ${result.gold_entities} vùng gán nhãn · ` +
          `${result.notes_with_fn} ghi chú còn ít nhất một phần bị bỏ sót`,
      );
      if (!result.micro) throw new Error(`Missing micro metrics for ${result.method}.`);
      const rows = [['Micro', result.micro] as const, ...Object.entries(result.by_label ?? {})];
      await expect(table.getByRole('rowheader')).toHaveText(rows.map(([label]) => label));
      for (const [label, metrics] of rows) {
        const row = table.getByRole('row').filter({
          has: page.getByRole('rowheader', { name: label, exact: true }),
        });
        await expect(row.getByRole('cell')).toHaveText(metricCells(metrics));
      }
      if (result.examples?.length) {
        await card.getByText('Ví dụ lỗi từ dữ liệu giả lập', { exact: true }).click();
        const examples = card.getByRole('listitem');
        await expect(examples).toHaveCount(result.examples.length);
        for (const [index, example] of result.examples.entries()) {
          await expect(examples.nth(index)).toContainText(example.note_id);
          if (example.text) await expect(examples.nth(index)).toContainText(example.text);
        }
      }
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(width);
    expect(pageErrors).toEqual([]);
  });
}

test('reopening without an artifact clears previously displayed evaluation', async ({ page }) => {
  await page.goto('/');
  const live = await openEvaluation(page);
  expect(live.status()).toBe(200);
  expect((await live.json()).status).toBe('available');
  await expect(page.getByRole('table', { name: 'Quy tắc', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Quay lại bàn rà soát', exact: true }).click();

  const unavailable = { status: 'unavailable', reason: 'Chưa có kết quả đánh giá.' };
  await page.route('**/api/evaluation', (route) =>
    route.fulfill({ status: 200, json: unavailable }),
  );
  const response = await openEvaluation(page);
  expect(await response.json()).toEqual(unavailable);
  await expect(page.getByRole('status')).toHaveText(unavailable.reason);
  await expect(page.getByRole('table')).toHaveCount(0);
  await expect(page.getByRole('alert')).toHaveCount(0);
});
