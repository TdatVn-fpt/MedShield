// apps/web/e2e/pdf-import.spec.ts — Verify local PDF import, review and download in Chromium.
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { expect, test } from '@playwright/test';
import type { Locator, Page } from '@playwright/test';

const demoPdf = fileURLToPath(
  new URL('../../../docs/evidence/demo-benh-an-ngoai-tru.pdf', import.meta.url),
);
const fixture = (file: string) =>
  fileURLToPath(new URL(`./fixtures/pdf/${file}`, import.meta.url));
const mixedPdf = fixture('mixed-text-scan.pdf');
const manualName = 'tạ hư cấu';
const followUp = '18/12';
const draft = 'Ghi chú giả lập đang soạn.';

/** controls finds the interactive PDF controls and the editable source text by their labels. */
function controls(page: Page) {
  return {
    file: page.getByLabel('Nhập PDF', { exact: true }),
    first: page.getByLabel('Trang đầu', { exact: true }),
    last: page.getByLabel('Trang cuối', { exact: true }),
    extract: page.getByRole('button', { name: 'Trích văn bản', exact: true }),
    cancel: page.getByRole('button', { name: 'Hủy nhập PDF', exact: true }),
    input: page.getByRole('textbox', { name: 'Văn bản gốc', exact: true }),
    alert: page.getByRole('alert'),
  };
}

/** selectManualName selects a known unmarked string in the rendered original text. */
async function selectManualName(source: Locator): Promise<void> {
  await source.evaluate((container, value) => {
    const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const node = walker.currentNode;
      const offset = node.textContent?.indexOf(value) ?? -1;
      if (offset < 0 || node.parentElement?.closest('mark')) continue;
      const range = new Range();
      range.setStart(node, offset);
      range.setEnd(node, offset + value.length);
      const selection = window.getSelection();
      selection?.removeAllRanges();
      selection?.addRange(range);
      container.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
      return;
    }
    throw new Error('The synthetic manual NAME was not found in an unmarked source range.');
  }, manualName);
}

/** downloadBytes activates an export by keyboard and reads the actual file from Chromium. */
async function downloadBytes(page: Page, name: string): Promise<Buffer> {
  const pending = page.waitForEvent('download');
  await page.getByRole('button', { name, exact: true }).press('Enter');
  return readFile(await (await pending).path());
}

for (const width of [390, 1440]) {
  test(`local PDF, hybrid review and approved TXT/JSON at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    const mutations: string[] = [];
    const consoleMessages: string[] = [];
    page.on('request', (request) => {
      if (!['GET', 'HEAD', 'OPTIONS'].includes(request.method())) {
        mutations.push(new URL(request.url()).pathname);
      }
    });
    page.on('console', (message) => consoleMessages.push(message.text()));
    await page.goto('/');
    const ui = controls(page);
    await ui.file.setInputFiles(demoPdf);
    await expect(ui.first).toHaveValue('1');
    await expect(ui.last).toHaveValue('2');
    await expect(ui.first).toBeFocused();
    await page.keyboard.press('Tab');
    await expect(ui.last).toBeFocused();
    await page.keyboard.press('Tab');
    await expect(ui.extract).toBeFocused();
    await page.keyboard.press('Enter');
    await expect(ui.input).toHaveValue(/tạ hư cấu/u);
    const text = await ui.input.inputValue();
    const expectedText = await readFile(demoPdf.replace(/\.pdf$/, '.expected.txt'), 'utf8');
    expect(text).toBe(expectedText.replaceAll('\r\n', '\n').trimEnd());
    expect(mutations).toEqual([]);

    await page.getByRole('combobox', { name: 'Phương pháp', exact: true }).selectOption('hybrid');
    const analyzed = page.waitForResponse((response) => response.url().endsWith('/api/analyze'));
    await page.getByRole('button', { name: 'Phân tích', exact: true }).press('Enter');
    const analysis = await analyzed;
    expect(analysis.status()).toBe(200);
    expect(analysis.request().postDataJSON()).toEqual({ text, language: 'vi', mode: 'hybrid' });
    const machine = await analysis.json();
    expect(machine.engine).toMatchObject({ mode: 'hybrid', status: 'available' });
    expect(machine.engine.model_revision).toMatch(/^sha256:[0-9a-f]{64}$/);
    const source = page.getByLabel('Văn bản gốc có đánh dấu', { exact: true });
    const preview = page.getByLabel('Bản đã che', { exact: true }).locator('.redacted-text');
    const approve = page.getByRole('checkbox', { name: 'Tôi đã rà soát toàn bộ nội dung' });
    const exportText = page.getByRole('button', { name: 'Tải TXT', exact: true });
    const exportJson = page.getByRole('button', { name: 'Tải JSON', exact: true });
    await expect(source).toBeVisible();
    await expect(exportText).toBeDisabled();
    await expect(exportJson).toBeDisabled();

    const nameIndex = text.indexOf(manualName);
    const start = Array.from(text.slice(0, nameIndex)).length;
    const end = start + Array.from(manualName).length;
    const overlap = machine.entities.findIndex(
      (entity: { start: number; end: number }) => entity.start < end && start < entity.end,
    );
    if (overlap >= 0) {
      await page.getByRole('button', { name: `Bỏ phát hiện ${overlap + 1}`, exact: true }).click();
    }
    await selectManualName(source);
    const redacted = page.waitForResponse((response) => {
      if (!response.url().endsWith('/api/redact')) return false;
      return response
        .request()
        .postDataJSON()
        .entities.some((entity: { source: string }) => entity.source === 'manual');
    });
    await page.getByRole('button', { name: 'Thêm vùng che', exact: true }).press('Enter');
    const review = await redacted;
    expect(review.status()).toBe(200);
    expect(review.request().postDataJSON().entities).toContainEqual({
      start,
      end,
      label: 'NAME',
      source: 'manual',
      score: 1,
    });
    const expected = await review.json();
    await expect.poll(() => preview.textContent()).toBe(expected.redacted_text);
    expect(expected.redacted_text).toContain(followUp);
    expect(expected.redacted_text).not.toContain(manualName);
    expect(expected.redacted_text).toMatch(/Đi cùng:\s*\[NAME_\d+\]/u);
    await expect(exportText).toBeDisabled();
    await approve.press('Space');
    await expect(approve).toBeChecked();

    expect(await downloadBytes(page, 'Tải TXT')).toEqual(Buffer.from(expected.redacted_text));
    const json = JSON.parse(
      new TextDecoder('utf-8', { fatal: true }).decode(await downloadBytes(page, 'Tải JSON')),
    );
    expect(Object.keys(json).sort()).toEqual(['metadata', 'redacted_text']);
    expect(json).toEqual(expected);
    await ui.file.setInputFiles(demoPdf);
    await expect(ui.first).toHaveValue('1');
    await ui.first.fill('2');
    await ui.extract.press('Enter');
    await expect(ui.input).toHaveValue(/Hẹn tái khám:\s*18\/12/u);
    await expect(ui.input).not.toHaveValue(/Hạ Minh/u);
    await expect(preview).toHaveCount(0);
    await expect(approve).not.toBeChecked();
    await expect(exportText).toBeDisabled();
    await expect(exportJson).toBeDisabled();
    expect(mutations).toContain('/api/analyze');
    expect(mutations.every((path) => ['/api/analyze', '/api/redact'].includes(path))).toBe(true);
    expect(
      await page.evaluate(() => [Object.entries(localStorage), Object.entries(sessionStorage)]),
    ).toEqual([[], []]);
    expect(consoleMessages.join('\n')).not.toContain(manualName);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(width);
  });
}

const malformedFiles = [
  {
    name: 'non-PDF bytes',
    upload: { name: 'fake.pdf', mimeType: 'application/pdf', buffer: Buffer.from('not a PDF') },
    message: /không có định dạng PDF/u,
  },
  {
    name: 'damaged PDF',
    upload: {
      name: 'damaged.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.7\n'),
    },
    message: /bị hỏng/u,
  },
  {
    name: 'password-protected PDF',
    upload: fixture('protected.pdf'),
    message: /yêu cầu mật khẩu/u,
  },
  {
    name: 'over 10 MiB',
    upload: {
      name: 'oversized.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.alloc(10 * 1024 * 1024 + 1),
    },
    message: /vượt 10 MiB/u,
  },
];

for (const { name, upload, message } of malformedFiles) {
  test(`PDF import rejects ${name} and preserves the draft`, async ({ page }) => {
    await page.goto('/');
    const ui = controls(page);
    await ui.input.fill(draft);
    await ui.file.setInputFiles(upload);
    await expect(ui.alert).toContainText(message);
    await expect(ui.input).toHaveValue(draft);
    await expect(ui.extract).toHaveCount(0);
  });
}

test('mixed pages require a narrower range and a scan alone stays out of the draft', async ({
  page,
}) => {
  await page.goto('/');
  const ui = controls(page);
  await ui.input.fill(draft);
  await ui.file.setInputFiles(mixedPdf);
  await expect(ui.last).toHaveValue('2');
  await ui.extract.click();
  await expect(ui.alert).toContainText(/Trang 2 không có lớp chữ/u);
  await expect(ui.input).toHaveValue(draft);
  await ui.first.fill('2');
  await ui.extract.click();
  await expect(ui.alert).toContainText(/Trang 2 không có lớp chữ/u);
  await expect(ui.input).toHaveValue(draft);
  await ui.first.fill('1');
  await ui.last.fill('1');
  await ui.extract.click();
  await expect(ui.input).toHaveValue('Synthetic text page one.');
});

test('invalid ranges, more than ten pages and oversized extracted text preserve the draft', async ({
  page,
}) => {
  await page.goto('/');
  const ui = controls(page);
  await ui.input.fill(draft);
  await ui.file.setInputFiles(fixture('limits.pdf'));
  await expect(ui.first).toHaveValue('1');
  await ui.first.fill('2');
  await ui.last.fill('1');
  await ui.extract.click();
  await expect(ui.alert).toContainText(/khoảng trang hợp lệ/u);
  await ui.first.fill('1');
  await ui.last.fill('11');
  await ui.extract.click();
  await expect(ui.alert).toContainText(/tối đa 10 trang/u);
  await ui.last.fill('10');
  await ui.extract.click();
  await expect(ui.alert).toContainText(/vượt 50\.000 ký tự/u);
  await expect(ui.input).toHaveValue(draft);
});

test('cancel and subsequent PDF import discard a held older file read', async ({ page }) => {
  await page.goto('/');
  const ui = controls(page);
  await ui.input.fill(draft);
  const gate = await page.evaluateHandle(() => {
    const read = File.prototype.arrayBuffer;
    let release!: () => void;
    const pending = new Promise<void>((resolve) => {
      release = resolve;
    });
    let started = false;
    let finished = false;
    File.prototype.arrayBuffer = async function () {
      if (this.name !== 'pdf-read-held.pdf') return read.call(this);
      started = true;
      await pending;
      const bytes = await read.call(this);
      finished = true;
      return bytes;
    };
    return { started: () => started, finished: () => finished, release };
  });
  await ui.file.setInputFiles({
    name: 'pdf-read-held.pdf',
    mimeType: 'application/pdf',
    buffer: await readFile(fixture('limits.pdf')),
  });
  try {
    await expect.poll(() => gate.evaluate((state) => state.started())).toBe(true);
    await ui.cancel.press('Enter');
    await expect(ui.input).toHaveValue(draft);
    await ui.file.setInputFiles(mixedPdf);
    await expect(ui.last).toHaveValue('2');
    await ui.last.fill('1');
    await ui.extract.press('Enter');
    await expect(ui.input).toHaveValue('Synthetic text page one.');
    await gate.evaluate((state) => state.release());
    await expect.poll(() => gate.evaluate((state) => state.finished())).toBe(true);
    await expect(ui.extract).toHaveCount(0);
    await expect(ui.alert).toHaveCount(0);
    await expect(ui.input).toHaveValue('Synthetic text page one.');
  } finally {
    await gate.evaluate((state) => state.release());
  }
});
