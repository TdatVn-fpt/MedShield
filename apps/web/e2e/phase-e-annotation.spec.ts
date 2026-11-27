// apps/web/e2e/phase-e-annotation.spec.ts — Verify the offline blind annotation workflow.
import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';
import { readFile } from 'node:fs/promises';

const tool = new URL('../../../scripts/phase-e-label/index.html', import.meta.url).href;
const notes = [
  { note_id: 'fixture-one', text: '🩺\r\nTên: Mai A\u0301nh.\r\nHẹn lại.' },
  { note_id: 'fixture-two', text: 'Ghi chú giả lập không có vùng định danh.' },
];
const packet = `${notes.map((note) => JSON.stringify(note)).join('\n')}\n`;

/** Load the blind fixture through the same file chooser an annotator uses. */
async function openPacket(page: Page) {
  await page.goto(tool);
  await page.getByLabel('Mở gói JSONL').setInputFiles({
    name: 'blind.jsonl',
    mimeType: 'application/x-ndjson',
    buffer: Buffer.from(packet),
  });
  await expect(page.getByRole('status')).toContainText('0/2');
}

/** Select a substring using the browser's native textarea coordinate system. */
async function selectValue(page: Page, selected: string) {
  await page.getByRole('textbox', { name: 'Văn bản gốc' }).evaluate((node, value) => {
    if (!(node instanceof HTMLTextAreaElement)) throw new Error('Missing text selection input');
    const start = node.value.indexOf(value);
    if (start < 0) throw new Error('Missing fixture selection');
    node.focus();
    node.setSelectionRange(start, start + value.length);
  }, selected);
}

test('exports original code point offsets offline and includes a reviewed negative note', async ({
  page,
  context,
}) => {
  const remote: string[] = [];
  page.on('request', (request) => {
    if (/^https?:/.test(request.url())) remote.push(request.url());
  });
  await context.setOffline(true);
  await page.setViewportSize({ width: 390, height: 844 });
  await openPacket(page);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  const exportButton = page.getByRole('button', { name: 'Xuất nhãn trả QA' });
  const confirm = page.getByRole('checkbox', { name: /Đã rà soát ghi chú này/ });
  await expect(exportButton).toBeDisabled();
  await selectValue(page, 'Mai A\u0301nh');
  await page.getByRole('button', { name: 'Thêm vùng đã chọn' }).click();
  await expect(page.getByRole('listitem')).toContainText('NAME');
  await page.getByRole('button', { name: 'Thêm vùng đã chọn' }).click();
  await expect(page.getByRole('status')).toContainText('chồng');
  await confirm.check();
  await page.getByRole('button', { name: 'Ghi chú sau' }).click();
  await expect(exportButton).toBeDisabled();
  await confirm.check();
  const [download] = await Promise.all([page.waitForEvent('download'), exportButton.click()]);
  const rows: unknown[] = (await readFile(await download.path(), 'utf8'))
    .trimEnd()
    .split('\n')
    .map((line: string) => JSON.parse(line));
  const start = Array.from(notes[0].text.split('Mai')[0]).length;
  const end = start + Array.from('Mai A\u0301nh').length;
  expect(rows).toEqual([
    { note_id: 'fixture-one', entities: [{ start, end, label: 'NAME' }] },
    { note_id: 'fixture-two', entities: [] },
  ]);
  expect(remote).toEqual([]);
});

test('restores an explicit draft and rejects a draft for different packet bytes', async ({
  page,
}) => {
  await openPacket(page);
  const checkbox = page.getByRole('checkbox', { name: /Đã rà soát ghi chú này/ });
  await checkbox.check();
  const [draft] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: 'Lưu tiến độ' }).click(),
  ]);
  const bytes = await readFile(await draft.path());
  expect(bytes.toString('utf8')).not.toContain(notes[0].text);
  await openPacket(page);
  const restore = page.getByLabel('Khôi phục tiến độ');
  await restore.setInputFiles({
    name: 'draft.json',
    mimeType: 'application/json',
    buffer: Buffer.from(
      bytes.toString('utf8').replace(/"packet_sha256":"[^"]+"/, '"packet_sha256":"bad"'),
    ),
  });
  await expect(page.getByRole('status')).toContainText('không thuộc gói');
  await restore.setInputFiles({ name: 'draft.json', mimeType: 'application/json', buffer: bytes });
  await expect(page.getByRole('status')).toContainText('1/2');
  await expect(page.getByRole('textbox', { name: 'Văn bản gốc' })).toHaveValue(notes[1].text);
  await expect(page.getByRole('button', { name: 'Xuất nhãn trả QA' })).toBeDisabled();
});
