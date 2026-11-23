// apps/web/e2e/review.spec.ts — Independent browser evidence for real analysis and edited exports.
import { mkdir, readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { expect, test } from '@playwright/test';
import type { Locator } from '@playwright/test';

const note =
  'Người bệnh Đỗ Minh Lâm, sinh ngày 12/04/1988, mã BN-90412. Ho khan hai ngày. Hẹn khám lại 23/12.';

/** selectText selects an exact substring across marked text nodes using DOM UTF-16 ranges. */
async function selectText(region: Locator, value: string): Promise<void> {
  await region.evaluate((element, selectedText) => {
    const text = element.textContent ?? '';
    const start = text.indexOf(selectedText);
    if (start < 0) throw new Error('Synthetic selection target is missing');
    const end = start + selectedText.length;
    const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
    const range = document.createRange();
    let offset = 0;
    let started = false;
    while (walker.nextNode()) {
      const node = walker.currentNode;
      const next = offset + (node.textContent?.length ?? 0);
      if (!started && start < next) {
        range.setStart(node, start - offset);
        started = true;
      }
      if (started && end <= next) {
        range.setEnd(node, end - offset);
        break;
      }
      offset = next;
    }
    const selection = window.getSelection();
    selection?.removeAllRanges();
    selection?.addRange(range);
    element.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
  }, value);
}

test('a new note uses the API and exports the reviewed TXT and minimal JSON', async ({ page }) => {
  const artifactDir = resolve(process.cwd(), '../../artifacts/local');
  await mkdir(artifactDir, { recursive: true });
  await page.goto('/');
  await page.getByRole('textbox', { name: 'Văn bản gốc', exact: true }).fill(note);
  const analyzed = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/analyze') && response.request().method() === 'POST',
  );
  await page.getByRole('button', { name: 'Phân tích', exact: true }).click();
  const response = await analyzed;
  expect(response.status()).toBe(200);
  const machine = await response.json();
  expect(machine.engine.mode).toBe('rules');
  await expect(page.getByLabel('Nhãn phát hiện 1', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Tải TXT', exact: true })).toBeDisabled();
  await page.screenshot({ path: resolve(artifactDir, 'G1-desktop.png'), fullPage: true });

  await page.getByLabel('Nhãn phát hiện 1', { exact: true }).selectOption('ADDR');
  const original = page.getByLabel('Văn bản gốc có đánh dấu', { exact: true });
  await selectText(original, 'Ho khan');
  await page.getByRole('button', { name: 'Thêm vùng che', exact: true }).click();
  await expect(page.getByLabel('Nhãn phát hiện 4', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Bỏ phát hiện 3', exact: true }).click();

  const expected =
    'Người bệnh [ADDR_1], sinh ngày [DOB_1], mã BN-90412. [NAME_1] hai ngày. Hẹn khám lại 23/12.';
  await expect(page.getByText(expected, { exact: true })).toBeVisible();
  await page.getByRole('checkbox', { name: 'Tôi đã rà soát toàn bộ nội dung' }).check();
  const txtEvent = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Tải TXT', exact: true }).click();
  const txtDownload = await txtEvent;
  const txtPath = await txtDownload.path();
  expect(txtPath).not.toBeNull();
  expect(await readFile(txtPath!, 'utf8')).toBe(expected);
  await txtDownload.saveAs(resolve(artifactDir, 'G1-reviewed.txt'));

  const jsonEvent = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Tải JSON', exact: true }).click();
  const jsonDownload = await jsonEvent;
  const jsonPath = await jsonDownload.path();
  const exported = JSON.parse(await readFile(jsonPath!, 'utf8'));
  expect(Object.keys(exported).sort()).toEqual(['metadata', 'redacted_text']);
  expect(exported.redacted_text).toBe(expected);
  expect(JSON.stringify(exported)).not.toContain('Đỗ Minh Lâm');
  expect(JSON.stringify(exported)).not.toContain('12/04/1988');
  await jsonDownload.saveAs(resolve(artifactDir, 'G1-reviewed.json'));
  await page.screenshot({ path: resolve(artifactDir, 'G1-reviewed-desktop.png'), fullPage: true });

  await page.getByRole('button', { name: 'Sửa văn bản', exact: true }).click();
  await page
    .getByRole('textbox', { name: 'Văn bản gốc', exact: true })
    .fill('Ghi chú mới không định danh.');
  await expect(page.getByRole('button', { name: 'Tải TXT', exact: true })).toBeDisabled();
  await expect(
    page.getByRole('checkbox', { name: 'Tôi đã rà soát toàn bộ nội dung' }),
  ).not.toBeChecked();
});

test('a late analysis response cannot restore an older input', async ({ page }) => {
  let release: () => void = () => {};
  let intercepted: () => void = () => {};
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  const received = new Promise<void>((resolve) => {
    intercepted = resolve;
  });
  await page.route('**/api/analyze', async (route) => {
    const result = await route.fetch();
    intercepted();
    await gate;
    await route.fulfill({ response: result });
  });
  await page.goto('/');
  await page.getByRole('textbox', { name: 'Văn bản gốc', exact: true }).fill(note);
  await page.getByRole('button', { name: 'Phân tích', exact: true }).click();
  await received;
  await page
    .getByRole('textbox', { name: 'Văn bản gốc', exact: true })
    .fill('Ghi chú mới không định danh.');
  const lateResponse = page.waitForResponse((response) => response.url().endsWith('/api/analyze'));
  release();
  await (await lateResponse).finished();
  await page.evaluate(
    () =>
      new Promise<void>((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
      ),
  );
  await expect(page.getByRole('textbox', { name: 'Văn bản gốc', exact: true })).toHaveValue(
    'Ghi chú mới không định danh.',
  );
  await expect(page.getByLabel('Nhãn phát hiện 1', { exact: true })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Tải TXT', exact: true })).toBeDisabled();
});

test('the backend unavailable engine state is visible and blocks export', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('combobox', { name: 'Ngôn ngữ', exact: true }).selectOption('en');
  await page.getByRole('combobox', { name: 'Phương pháp', exact: true }).selectOption('ner');
  await page.getByRole('textbox', { name: 'Văn bản gốc', exact: true }).fill(note);
  const unavailable = page.waitForResponse(
    (response) => response.url().endsWith('/api/analyze') && response.status() === 503,
  );
  await page.getByRole('button', { name: 'Phân tích', exact: true }).click();
  expect((await unavailable).status()).toBe(503);
  await expect(page.getByRole('alert')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Tải TXT', exact: true })).toBeDisabled();
  await expect(page.getByLabel('Nhãn phát hiện 1', { exact: true })).toHaveCount(0);
});

test('responsive layout at 390px viewport renders correctly', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await page.getByRole('textbox', { name: 'Văn bản gốc', exact: true }).fill(note);
  const analyzed = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/analyze') && response.request().method() === 'POST',
  );
  await page.getByRole('button', { name: 'Phân tích', exact: true }).click();
  await analyzed;
  await expect(page.getByLabel('Nhãn phát hiện 1', { exact: true })).toBeVisible();
  const markedSource = page.getByLabel('Văn bản gốc có đánh dấu', { exact: true });
  await expect(markedSource).toBeVisible();
  const source = page.getByRole('region', { name: 'Bản gốc' });
  const preview = page.getByRole('region', { name: 'Bản đã che' });
  await expect(page.getByRole('heading', { name: /Các vùng được phát hiện/ })).toBeVisible();
  const sourceBox = (await source.boundingBox())!;
  const previewBox = (await preview.boundingBox())!;
  expect(previewBox.y).toBeGreaterThanOrEqual(sourceBox.y + sourceBox.height);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390);
  await page.getByRole('checkbox', { name: 'Tôi đã rà soát toàn bộ nội dung' }).check();
  await expect(page.getByRole('button', { name: 'Tải TXT', exact: true })).toBeEnabled();
  await page.screenshot({
    path: resolve(process.cwd(), '../../artifacts/local', 'G1-mobile-390px.png'),
    fullPage: true,
  });
});

test('responsive layout at 1440px viewport renders correctly', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/');
  await page.getByRole('textbox', { name: 'Văn bản gốc', exact: true }).fill(note);
  const analyzed = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/analyze') && response.request().method() === 'POST',
  );
  await page.getByRole('button', { name: 'Phân tích', exact: true }).click();
  await analyzed;
  await expect(page.getByLabel('Nhãn phát hiện 1', { exact: true })).toBeVisible();
  const markedSource = page.getByLabel('Văn bản gốc có đánh dấu', { exact: true });
  await expect(markedSource).toBeVisible();
  const source = page.getByRole('region', { name: 'Bản gốc' });
  const preview = page.getByRole('region', { name: 'Bản đã che' });
  await expect(page.getByRole('heading', { name: /Các vùng được phát hiện/ })).toBeVisible();
  const sourceBox = (await source.boundingBox())!;
  const previewBox = (await preview.boundingBox())!;
  expect(previewBox.x).toBeGreaterThanOrEqual(sourceBox.x + sourceBox.width);
  expect(previewBox.y).toBe(sourceBox.y);
  await page.screenshot({
    path: resolve(process.cwd(), '../../artifacts/local', 'G1-desktop-1440px.png'),
    fullPage: true,
  });
});

test('unicode combining marks, crlf, and emoji preserve correctly in preview', async ({
  page,
}) => {
  const unicodeText =
    'Bệnh nhân: Hà Tiến Đạt\r\nĐiện thoại: 0123456789̇ (chấm trên)\nEmoji: 👨‍⚕️ bác sĩ';
  await page.goto('/');
  await page.getByRole('textbox', { name: 'Văn bản gốc', exact: true }).fill(unicodeText);
  const analyzed = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/analyze') && response.request().method() === 'POST',
  );
  await page.getByRole('button', { name: 'Phân tích', exact: true }).click();
  const response = await analyzed;
  expect(response.status()).toBe(200);
  await expect(page.getByLabel('Nhãn phát hiện 1', { exact: true })).toBeVisible();
  const markedSourceText = await page
    .getByLabel('Văn bản gốc có đánh dấu', { exact: true })
    .textContent();
  expect(markedSourceText).toContain('0123456789̇');
  expect(markedSourceText).toContain('👨‍⚕️');
  expect(markedSourceText).toContain('Hà Tiến Đạt');
});
